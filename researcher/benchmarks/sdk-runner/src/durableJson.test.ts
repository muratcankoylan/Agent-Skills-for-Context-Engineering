import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  DurableJsonError,
  canonicalFileBytes,
  canonicalJsonBytes,
  canonicalize,
  domainSeparatedDigest,
  parseCanonicalFile,
  parseJsonStrict,
  sha256Bytes,
} from "./durableJson.ts";
import type { JsonValue } from "./durableJson.ts";

interface CanonicalizationCase {
  id: string;
  input_json: string;
  valid: boolean;
  expected_canonical?: string;
  expected_digest?: string;
  expected_code?: string;
}

function assertCode(source: () => unknown, code: string): void {
  assert.throws(
    source,
    (error: unknown) => error instanceof DurableJsonError && error.code === code,
  );
}

test("matches every repository canonicalization vector byte-for-byte", () => {
  const srcDir = dirname(fileURLToPath(import.meta.url));
  const fixturePath = resolve(srcDir, "../../../schemas/fixtures/canonicalization-v1.json");
  const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
    profile: string;
    cases: CanonicalizationCase[];
  };
  assert.equal(fixture.profile, "jcs-rfc8785-integer-v1");
  assert.equal(fixture.cases.length, 12);

  for (const vector of fixture.cases) {
    if (!vector.valid) {
      assertCode(() => parseJsonStrict(vector.input_json), vector.expected_code as string);
      continue;
    }
    const value = parseJsonStrict(vector.input_json);
    const expectedBytes = Buffer.from(vector.expected_canonical as string, "utf8");
    assert.deepEqual(canonicalJsonBytes(value), expectedBytes, vector.id);
    assert.equal(canonicalize(value), vector.expected_canonical, vector.id);
    assert.equal(sha256Bytes(expectedBytes), vector.expected_digest, vector.id);
  }
});

test("strict parsing rejects duplicate, unsafe, invalid, and trailing input", () => {
  assertCode(() => parseJsonStrict('{"a":1,"\\u0061":2}'), "DUPLICATE_KEY");
  for (const source of ["1.5", "1e0", "-0", "9007199254740992", "NaN", "Infinity", "-Infinity"]) {
    assertCode(() => parseJsonStrict(source), "UNSAFE_NUMBER");
  }
  for (const source of ["", "null false", "[1,]", '{"a":1,}', "01", '"unterminated']) {
    assertCode(() => parseJsonStrict(source), "INVALID_JSON");
  }
  assertCode(() => parseJsonStrict('"\\ud800"'), "INVALID_UNICODE");
  assertCode(() => canonicalize("\ud800"), "INVALID_UNICODE");
});

test("canonical files admit canonical JSON followed by exactly one LF", () => {
  const value = parseJsonStrict('{"z":1,"a":"é"}');
  const file = Buffer.from('{"a":"é","z":1}\n', "utf8");
  assert.deepEqual(canonicalFileBytes(value), file);
  assert.deepEqual(parseCanonicalFile(file), { a: "é", z: 1 });

  for (const source of [
    '{"a":"é","z":1}',
    '{"a":"é","z":1}\r\n',
    '{"a":"é","z":1}\n\n',
    '{ "a":"é","z":1 }\n',
    '{"z":1,"a":"é"}\n',
  ]) {
    assertCode(() => parseCanonicalFile(source), "NON_CANONICAL");
  }
  assertCode(
    () => parseCanonicalFile(Buffer.from([0x7b, 0x22, 0xff, 0x22, 0x3a, 0x31, 0x7d, 0x0a])),
    "INVALID_JSON",
  );
});

test("canonicalizer rejects non-JSON values and array holes", () => {
  const sparse: JsonValue[] = [];
  sparse.length = 1;
  assertCode(() => canonicalize(sparse), "INVALID_JSON");
  assertCode(() => canonicalize(1.25), "UNSAFE_NUMBER");
  assertCode(() => canonicalize(-0), "UNSAFE_NUMBER");
  assertCode(() => canonicalize(undefined as unknown as JsonValue), "INVALID_JSON");
});

test("domain separation is full, deterministic, and boundary-safe", () => {
  const first = domainSeparatedDigest("router-plan-item/v1", Buffer.from("abc"));
  assert.match(first, /^sha256:[0-9a-f]{64}$/);
  assert.equal(first, domainSeparatedDigest("router-plan-item/v1", Buffer.from("abc")));
  assert.notEqual(first, domainSeparatedDigest("router-plan/v1", Buffer.from("abc")));
  assert.notEqual(first, domainSeparatedDigest("router-plan-item/v1", Buffer.from("abcd")));
  assert.notEqual(
    domainSeparatedDigest("a", Buffer.from("bc")),
    domainSeparatedDigest("ab", Buffer.from("c")),
  );
  assertCode(() => domainSeparatedDigest("bad\0domain", Buffer.alloc(0)), "INVALID_DIGEST");
});
