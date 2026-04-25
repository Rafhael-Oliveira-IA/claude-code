/**
 * Stub for color-diff-napi
 * Native syntax highlighting/diff coloring — Anthropic internal native module.
 * Falls back to no-op; syntax highlighting will be disabled.
 */

export class ColorDiff {
  constructor(_options) {}
  colorize(_text, _lang) { return _text }
}

export class ColorFile {
  constructor(_options) {}
  colorize(_text, _lang) { return _text }
}

export function getSyntaxTheme(_theme) {
  return null
}
