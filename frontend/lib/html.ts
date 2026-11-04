/**
 * Escaping for the two HTML contexts this app builds by hand.
 *
 * The map screens render a Leaflet map inside a `react-native-webview`
 * by writing an HTML document as a string. That document has two
 * injection points, and both need care:
 *
 * 1. **Inside a `<script>` block.** `JSON.stringify()` does not escape
 *    `<`, so a value containing `</script>` ends the script block early
 *    and everything after it is parsed as markup. `jsonForScript()`
 *    escapes `<`, `>` and `&` as unicode sequences, which are still
 *    valid JSON but cannot close the tag.
 *
 * 2. **Inside HTML.** A vehicle's registration number, a driver's name
 *    and a branch's name are all free text that a user can type. They
 *    are rendered into a Leaflet popup, so they must be escaped for the
 *    HTML context or a stored XSS lands in the WebView — which has
 *    network access and can talk back to the app through
 *    `window.ReactNativeWebView.postMessage`.
 *
 * Every value that comes from the database and ends up in that HTML
 * goes through one of these two functions.
 */

const HTML_ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/** Escape a value for interpolation into HTML text or an attribute. */
export function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c] ?? c);
}

/**
 * Serialise a value for interpolation into a `<script>` block.
 *
 * The result is still valid JSON — `<` becomes `<` and so on —
 * but no value can close the surrounding tag or start a new one.
 */
export function jsonForScript(value: unknown): string {
  return JSON.stringify(value ?? null)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}
