/**
 * Preload: define MACRO global for running without bun build.
 * In production, MACRO constants are inlined at build time via --define.
 */
// @ts-ignore
globalThis.MACRO = {
  VERSION: '1.0.99-local',
  BUILD_TIME: new Date().toISOString(),
}
