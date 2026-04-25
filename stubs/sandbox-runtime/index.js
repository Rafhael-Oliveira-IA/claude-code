/**
 * Stub for @anthropic-ai/sandbox-runtime
 * Sandbox features are only supported on Linux. This stub safely disables them.
 */

export class SandboxViolationStore {
  getViolations() { return [] }
  addViolation(_event) {}
  clear() {}
}

const noop = () => {}
const returnFalse = () => false
const returnNull = () => null
const returnUndefined = () => undefined

export const SandboxManager = {
  isSupportedPlatform() { return false },
  async checkDependencies(_config) {
    return { supported: false, missing: [], optional: [] }
  },
  async wrapWithSandbox(_config, fn) { return fn() },
  async initialize(_config, _callback) {},
  updateConfig(_config) {},
  async reset() {},
  getFsReadConfig: returnNull,
  getFsWriteConfig: returnNull,
  getNetworkRestrictionConfig: returnNull,
  getIgnoreViolations: returnFalse,
  getAllowUnixSockets: returnFalse,
  getAllowLocalBinding: returnFalse,
  getEnableWeakerNestedSandbox: returnFalse,
  getProxyPort: returnNull,
  getSocksProxyPort: returnNull,
  getLinuxHttpSocketPath: returnNull,
  getSandboxViolationStore() { return new SandboxViolationStore() },
  isActive() { return false },
  cleanupAfterCommand: noop,
}

export const SandboxRuntimeConfigSchema = {
  parse(data) { return data },
  safeParse(data) { return { success: true, data } },
  optional() { return this },
}
