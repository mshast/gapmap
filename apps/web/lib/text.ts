/** Resume evidence is copied verbatim, so a leading list marker is not part of the claim. */
export function cleanQuote(value: string): string {
  return value.replace(/^[\s\-*•–—-]+/, "").trim();
}
