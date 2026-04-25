/**
 * Stub for @anthropic-ai/mcpb
 * MCP bundle (.dxt) support — no-op stub for local use.
 */

export const McpbManifestSchema = {
  parse(data) { return data },
  safeParse(data) { return { success: true, data } },
}

export async function getMcpConfigForManifest(_manifest) {
  return null
}
