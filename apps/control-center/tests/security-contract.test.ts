import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  apiContentSecurityPolicy,
  buildContentSecurityPolicy,
} from "../lib/security.ts";

function channelToLinear(channel: number): number {
  const value = channel / 255;
  return value <= 0.04045
    ? value / 12.92
    : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)
    ?.map((channel) => channelToLinear(Number.parseInt(channel, 16)));
  assert.ok(channels);
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(first: string, second: string): number {
  const brighter = Math.max(luminance(first), luminance(second));
  const darker = Math.min(luminance(first), luminance(second));
  return (brighter + 0.05) / (darker + 0.05);
}

test("production page CSP uses a strict Next-compatible nonce policy", () => {
  const nonce = "0123456789abcdefghijklmn";
  const policy = buildContentSecurityPolicy(nonce, "production");

  assert.match(policy, new RegExp(`script-src [^;]*'nonce-${nonce}'`));
  assert.match(policy, /'strict-dynamic'/);
  assert.match(policy, /script-src-attr 'none'/);
  assert.match(policy, /style-src-attr 'none'/);
  assert.match(policy, /object-src 'none'/);
  assert.match(policy, /frame-ancestors 'none'/);
  assert.doesNotMatch(policy, /'unsafe-inline'|'unsafe-eval'/);
});

test("development CSP limits relaxations to framework requirements", () => {
  const policy = buildContentSecurityPolicy(
    "0123456789abcdefghijklmn",
    "development",
  );
  assert.match(policy, /script-src [^;]*'unsafe-eval'/);
  assert.match(policy, /style-src [^;]*'unsafe-inline'/);
  assert.match(policy, /connect-src [^;]* ws:/);
  assert.match(policy, /script-src-attr 'none'/);
});

test("CSP construction rejects values that could escape a directive", () => {
  assert.throws(
    () => buildContentSecurityPolicy("short", "production"),
    /nonce/i,
  );
  assert.throws(
    () =>
      buildContentSecurityPolicy(
        "0123456789abcdefghijklmn'; script-src *",
        "production",
      ),
    /nonce/i,
  );
});

test("JSON APIs use a deny-all document policy", () => {
  assert.match(apiContentSecurityPolicy, /^default-src 'none'/);
  assert.match(apiContentSecurityPolicy, /base-uri 'none'/);
  assert.match(apiContentSecurityPolicy, /frame-ancestors 'none'/);
});

test("small muted text color contracts meet WCAG AA contrast", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /--muted:\s*#5f675b/);
  assert.match(css, /\.deployment-facts dt\s*\{[\s\S]*?color:\s*#899483/);
  assert.ok(contrastRatio("#5f675b", "#e7e6dc") >= 4.5);
  assert.ok(contrastRatio("#899483", "#24291f") >= 4.5);
});
