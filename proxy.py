"""
proxy.py - Proxy Anthropic -> OpenAI
Traduz /v1/messages (Anthropic) para /v1/chat/completions (OpenAI)
Roda com: python proxy.py
Requer: pip install flask requests
"""

import json
import os
import re
import sys
import requests
from flask import Flask, request, Response, jsonify

# --- Carregar chave ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    key_file = os.path.join(os.path.dirname(__file__), ".env.openai-key")
    try:
        with open(key_file, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"OPENAI_API_KEY=(.+)", line.strip())
                if m:
                    OPENAI_API_KEY = m.group(1).strip()
                    break
    except FileNotFoundError:
        pass

if not OPENAI_API_KEY:
    print("ERRO: Defina OPENAI_API_KEY em .env.openai-key ou na variavel de ambiente.")
    sys.exit(1)

OPENAI_MODEL_MAP = {
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
    "claude-3-5-sonnet-20241022": "gpt-4o",
    "claude-3-5-haiku-20241022": "gpt-4o-mini",
    "claude-opus-4-5": "gpt-4o",
    "claude-sonnet-4-5": "gpt-4o",
}

app = Flask(__name__)


def map_model(model):
    return OPENAI_MODEL_MAP.get(model, model)


def anthropic_to_openai_messages(messages, system=None):
    result = []
    if system:
        if isinstance(system, str):
            result.append({"role": "system", "content": system})
        elif isinstance(system, list):
            text = "\n".join(b.get("text", "") for b in system if b.get("type") == "text")
            if text:
                result.append({"role": "system", "content": text})
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            result.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            text = "\n".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            )
            result.append({"role": msg["role"], "content": text})
    return result


def openai_to_anthropic_response(oai_resp, original_model):
    choice = oai_resp.get("choices", [{}])[0]
    text = choice.get("message", {}).get("content", "")
    usage = oai_resp.get("usage", {})
    return {
        "id": f"msg_{oai_resp.get('id', 'local')}",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "model": original_model,
        "stop_reason": "end_turn" if choice.get("finish_reason") == "stop" else choice.get("finish_reason"),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def stream_openai_to_anthropic(oai_stream_resp, original_model):
    """Converte SSE do OpenAI para SSE do Anthropic."""
    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': 'msg_stream', 'type': 'message', 'role': 'assistant', 'content': [], 'model': original_model, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

    for line in oai_stream_resp.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        data = line[6:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
            if delta:
                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': delta}})}\n\n"
        except json.JSONDecodeError:
            pass

    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 0}})}\n\n"
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


@app.route("/health")
def health():
    return "ok", 200


@app.route("/v1/messages", methods=["POST"])
def messages():
    body = request.get_json(force=True)
    original_model = body.get("model", "gpt-4o")
    oai_model = map_model(original_model)
    messages_oai = anthropic_to_openai_messages(body.get("messages", []), body.get("system"))
    stream = body.get("stream", False)

    payload = {
        "model": oai_model,
        "messages": messages_oai,
        "max_tokens": body.get("max_tokens", 4096),
        "stream": stream,
    }
    if "temperature" in body:
        payload["temperature"] = body["temperature"]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        oai_resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            stream=stream,
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": {"message": str(e), "type": "connection_error"}}), 500

    if not oai_resp.ok:
        err = oai_resp.text
        print(f"[proxy] OpenAI erro {oai_resp.status_code}: {err}")
        return Response(
            json.dumps({"error": {"message": err, "type": "api_error"}}),
            status=oai_resp.status_code,
            mimetype="application/json",
        )

    if stream:
        return Response(
            stream_openai_to_anthropic(oai_resp, original_model),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        return jsonify(openai_to_anthropic_response(oai_resp.json(), original_model))


if __name__ == "__main__":
    print(f"[proxy] Rodando em http://127.0.0.1:4000")
    print(f"[proxy] Chave: {OPENAI_API_KEY[:8]}...")
    app.run(host="127.0.0.1", port=4000, debug=False)
