import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { test } from "node:test";

// Exercise the transitive instance AJV actually resolves, including if npm nests
// it later. This does not add URI construction to the contract package's API.
const require = createRequire(import.meta.url);
const requireFromAjv = createRequire(require.resolve("ajv"));
const uri = requireFromAjv("fast-uri") as typeof import("fast-uri");

test("AJV resolves the exact fast-uri security patch", () => {
  assert.equal(require("ajv/package.json").version, "8.20.0");
  assert.equal(requireFromAjv("fast-uri/package.json").version, "3.1.7");
});

test("URI composition rejects port authority injection and malformed delimiters", () => {
  // GHSA-qw65-cvwx-89v3: 3.1.5 accepted the first payload and produced
  // http://trusted.example:@127.0.0.1:8124/app, changing the parsed hostname.
  // https://github.com/fastify/fast-uri/security/advisories/GHSA-qw65-cvwx-89v3
  for (const port of [
    "@127.0.0.1:8124",
    "80@attacker.example",
    "8080/path",
    "8080?redirect=1",
    "8080#fragment",
    "\r\nHost: attacker.example",
    "-1",
    "NaN",
  ]) {
    const components = { scheme: "http", host: "trusted.example", port, path: "/app" };
    assert.throws(() => uri.serialize({ ...components }), `serialize must reject ${JSON.stringify(port)}`);
    assert.throws(() => uri.normalize({ ...components }), `normalize must reject ${JSON.stringify(port)}`);
  }
});

test("valid numeric ports preserve the configured authority", () => {
  for (const port of [8080, "8124", ""]) {
    const serialized = uri.serialize({ scheme: "http", host: "trusted.example", port, path: "/app" });
    const parsed = new URL(serialized);
    assert.equal(parsed.hostname, "trusted.example");
    assert.equal(parsed.username, "");
    assert.equal(parsed.port, String(port));
    assert.equal(parsed.pathname, "/app");
  }
});
