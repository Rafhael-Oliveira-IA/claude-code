/**
 * Stub for TungstenTool — internal Anthropic-only tool.
 * Only included when USER_TYPE=ant (see tools.ts line 215).
 * This stub is a safe no-op placeholder.
 */

export const TungstenTool = {
  name: 'tungsten',
  displayName: 'Tungsten',
  description: 'Internal tool (stub)',
  inputSchema: { type: 'object', properties: {} },
  isEnabled: () => false,
  isConcurrencySafe: () => false,
  isReadOnly: () => true,
  isDestructive: () => false,
  checkPermissions: async (input) => ({ behavior: 'allow', updatedInput: input }),
  toAutoClassifierInput: () => '',
  userFacingName: () => 'tungsten',
  async call() { return { type: 'text', text: 'Not supported' } },
  renderToolUseMessage: () => null,
  renderToolResultMessage: () => null,
  renderToolUseErrorMessage: () => null,
}
