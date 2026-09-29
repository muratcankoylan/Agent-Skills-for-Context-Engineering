const noncePattern = /^[A-Za-z0-9_-]{24,128}$/;

export function buildContentSecurityPolicy(
  nonce: string,
  environment: "development" | "production",
): string {
  if (!noncePattern.test(nonce)) {
    throw new Error("CSP nonce must be an unpadded base64url-compatible value.");
  }

  const developmentScriptSource =
    environment === "development" ? " 'unsafe-eval'" : "";
  const developmentStyleSource =
    environment === "development" ? " 'unsafe-inline'" : "";
  const developmentConnectSource = environment === "development" ? " ws:" : "";

  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${developmentScriptSource}`,
    "script-src-attr 'none'",
    `style-src 'self' 'nonce-${nonce}'${developmentStyleSource}`,
    "style-src-attr 'none'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src 'self'${developmentConnectSource}`,
    "media-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-src 'none'",
    "frame-ancestors 'none'",
    "worker-src 'none'",
    "manifest-src 'self'",
  ].join("; ");
}

export const apiContentSecurityPolicy = [
  "default-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
].join("; ");
