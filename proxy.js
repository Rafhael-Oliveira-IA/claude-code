/**
 * proxy.js — mini proxy Anthropic→OpenAI
 * Roda com: bun proxy.js
 * Traduz chamadas /v1/messages (formato Anthropic) para /v1/chat/completions (OpenAI)
 */

// Load key from .env.openai-key if not set in environment
let OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  try {
    const keyFile = import.meta.dir + '/.env.openai-key';
    const content = await Bun.file(keyFile).text();
    const match = content.match(/OPENAI_API_KEY=(.+)/);
    if (match) OPENAI_API_KEY = match[1].trim();
  } catch {}
}
const OPENAI_MODEL_MAP = {
  'gpt-4o': 'gpt-4o',
  'gpt-4o-mini': 'gpt-4o-mini',
  'claude-3-5-sonnet-20241022': 'gpt-4o',
  'claude-3-5-haiku-20241022': 'gpt-4o-mini',
  'claude-opus-4-5': 'gpt-4o',
  'claude-sonnet-4-5': 'gpt-4o',
};

if (!OPENAI_API_KEY) {
  console.error('❌  Defina OPENAI_API_KEY antes de rodar.');
  process.exit(1);
}

function mapModel(model) {
  return OPENAI_MODEL_MAP[model] ?? model;
}

function anthropicMessagesToOpenAI(messages, system) {
  const result = [];
  if (system) result.push({ role: 'system', content: system });
  for (const msg of messages) {
    if (typeof msg.content === 'string') {
      result.push({ role: msg.role, content: msg.content });
    } else if (Array.isArray(msg.content)) {
      const text = msg.content
        .filter(b => b.type === 'text')
        .map(b => b.text)
        .join('\n');
      result.push({ role: msg.role, content: text });
    }
  }
  return result;
}

function openAIResponseToAnthropic(oai, model) {
  const choice = oai.choices?.[0];
  const text = choice?.message?.content ?? '';
  return {
    id: `msg_${oai.id}`,
    type: 'message',
    role: 'assistant',
    content: [{ type: 'text', text }],
    model,
    stop_reason: choice?.finish_reason === 'stop' ? 'end_turn' : choice?.finish_reason,
    stop_sequence: null,
    usage: {
      input_tokens: oai.usage?.prompt_tokens ?? 0,
      output_tokens: oai.usage?.completion_tokens ?? 0,
    },
  };
}

async function* openAIStreamToAnthropic(stream, model) {
  // Start event
  yield `event: message_start\ndata: ${JSON.stringify({
    type: 'message_start',
    message: { id: 'msg_stream', type: 'message', role: 'assistant', content: [], model, stop_reason: null, stop_sequence: null, usage: { input_tokens: 0, output_tokens: 0 } }
  })}\n\n`;
  yield `event: content_block_start\ndata: ${JSON.stringify({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })}\n\n`;

  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6).trim();
      if (data === '[DONE]') continue;
      try {
        const chunk = JSON.parse(data);
        const delta = chunk.choices?.[0]?.delta?.content;
        if (delta) {
          yield `event: content_block_delta\ndata: ${JSON.stringify({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: delta } })}\n\n`;
        }
      } catch {}
    }
  }

  yield `event: content_block_stop\ndata: ${JSON.stringify({ type: 'content_block_stop', index: 0 })}\n\n`;
  yield `event: message_delta\ndata: ${JSON.stringify({ type: 'message_delta', delta: { stop_reason: 'end_turn', stop_sequence: null }, usage: { output_tokens: 0 } })}\n\n`;
  yield `event: message_stop\ndata: ${JSON.stringify({ type: 'message_stop' })}\n\n`;
}

const server = Bun.serve({
  port: 4000,
  async fetch(req) {
    const url = new URL(req.url);

    // Health check
    if (url.pathname === '/health') {
      return new Response('ok', { status: 200 });
    }

    // Anthropic messages endpoint
    if (url.pathname === '/v1/messages' && req.method === 'POST') {
      let body;
      try {
        body = await req.json();
      } catch {
        return new Response('Bad request', { status: 400 });
      }

      const oaiModel = mapModel(body.model ?? 'gpt-4o');
      const messages = anthropicMessagesToOpenAI(body.messages ?? [], body.system);
      const stream = body.stream ?? false;

      const oaiPayload = {
        model: oaiModel,
        messages,
        max_tokens: body.max_tokens ?? 4096,
        stream,
        ...(body.temperature !== undefined && { temperature: body.temperature }),
      };

      const oaiResp = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(oaiPayload),
      });

      if (!oaiResp.ok) {
        const err = await oaiResp.text();
        console.error(`❌  OpenAI error ${oaiResp.status}:`, err);
        return new Response(JSON.stringify({ error: { message: err, type: 'api_error' } }), {
          status: oaiResp.status,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (stream) {
        const readable = new ReadableStream({
          async start(controller) {
            const encoder = new TextEncoder();
            for await (const chunk of openAIStreamToAnthropic(oaiResp.body, body.model)) {
              controller.enqueue(encoder.encode(chunk));
            }
            controller.close();
          },
        });
        return new Response(readable, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        });
      }

      const oaiData = await oaiResp.json();
      const anthropicData = openAIResponseToAnthropic(oaiData, body.model);
      return new Response(JSON.stringify(anthropicData), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Catch-all: log e retorna 404
    console.log(`[proxy] ${req.method} ${url.pathname} → 404`);
    return new Response('Not found', { status: 404 });
  },
});

console.log(`✅  Proxy Anthropic→OpenAI rodando em http://localhost:${server.port}`);
console.log(`    Modelo: ${process.env.ANTHROPIC_MODEL ?? 'gpt-4o'}`);
