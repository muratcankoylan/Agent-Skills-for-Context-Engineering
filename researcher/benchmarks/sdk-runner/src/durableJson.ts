/**
 * Runner-private durable JSON codec.
 *
 * This deliberately mirrors the repository's jcs-rfc8785-integer-v1
 * contract without importing the separately packaged schema runtime. It is a
 * pre-activation boundary for benchmark state, not a registry claim.
 */

import { createHash } from "node:crypto";

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export type Sha256Digest = `sha256:${string}`;

export type DurableJsonErrorCode =
  | "DUPLICATE_KEY"
  | "INVALID_DIGEST"
  | "INVALID_JSON"
  | "INVALID_UNICODE"
  | "NON_CANONICAL"
  | "UNSAFE_NUMBER";

/** Stable, non-sensitive failure at the runner's durable JSON boundary. */
export class DurableJsonError extends Error {
  readonly code: DurableJsonErrorCode;
  readonly safeMessage: string;

  constructor(code: DurableJsonErrorCode, safeMessage: string) {
    super(`[${code}] ${safeMessage}`);
    this.name = "DurableJsonError";
    this.code = code;
    this.safeMessage = safeMessage;
  }
}

const SAFE_INTEGER_MAX = 9_007_199_254_740_991n;
const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/;
const DOMAIN_PATTERN = /^[a-z0-9][a-z0-9./_-]*$/;
const DOMAIN_FRAME = Buffer.from("researcher-sdk-runner-digest/v1\0", "ascii");

/** Parse the integer-only I-JSON profile without silent key or number coercion. */
export function parseJsonStrict(text: string): JsonValue {
  return new StrictJsonParser(text).parse();
}

/** Serialize the RFC 8785 subset used by durable organization records. */
export function canonicalize(value: JsonValue): string {
  if (value === null) {
    return "null";
  }
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || Object.is(value, -0)) {
      throw new DurableJsonError(
        "UNSAFE_NUMBER",
        "canonical records admit only non-negative-zero safe integers",
      );
    }
    return String(value);
  }
  if (typeof value === "string") {
    return quoteString(value);
  }
  if (Array.isArray(value)) {
    const parts: string[] = [];
    for (let index = 0; index < value.length; index += 1) {
      if (!Object.hasOwn(value, index)) {
        throw new DurableJsonError("INVALID_JSON", "JSON arrays cannot contain holes");
      }
      parts.push(canonicalize(value[index] as JsonValue));
    }
    return `[${parts.join(",")}]`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value);
    for (const key of keys) {
      validateUnicode(key);
    }
    keys.sort(compareUtf16);
    return `{${keys
      .map((key) => `${quoteString(key)}:${canonicalize(value[key] as JsonValue)}`)
      .join(",")}}`;
  }
  throw new DurableJsonError("INVALID_JSON", "unsupported JSON value type");
}

/** Canonical JSON bytes without a record terminator. */
export function canonicalJsonBytes(value: JsonValue): Buffer {
  return Buffer.from(canonicalize(value), "utf8");
}

/** The only admitted durable file form: canonical JSON followed by one LF. */
export function canonicalFileBytes(value: JsonValue): Buffer {
  return Buffer.concat([canonicalJsonBytes(value), Buffer.from("\n", "ascii")]);
}

/** Parse a canonical durable file and reject every alternate byte spelling. */
export function parseCanonicalFile(source: string | Uint8Array): JsonValue {
  let text: string;
  let bytes: Buffer;
  if (typeof source === "string") {
    text = source;
    bytes = Buffer.from(source, "utf8");
  } else {
    bytes = Buffer.from(source);
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch {
      throw new DurableJsonError("INVALID_JSON", "durable JSON is not valid UTF-8");
    }
  }
  const value = parseJsonStrict(text);
  if (!bytes.equals(canonicalFileBytes(value))) {
    throw new DurableJsonError(
      "NON_CANONICAL",
      "durable JSON must be canonical JSON followed by exactly one LF",
    );
  }
  return value;
}

/** Raw SHA-256 over exact bytes. */
export function sha256Bytes(body: string | Uint8Array): Sha256Digest {
  return `sha256:${createHash("sha256").update(body).digest("hex")}`;
}

/**
 * Domain-separated SHA-256 with length-framed domain and payload.
 *
 * The frame prevents a domain or payload boundary from being reinterpreted;
 * callers still use distinct, versioned domains for distinct record kinds.
 */
export function domainSeparatedDigest(
  domain: string,
  payload: string | Uint8Array,
): Sha256Digest {
  if (!DOMAIN_PATTERN.test(domain)) {
    throw new DurableJsonError("INVALID_DIGEST", "digest domain is not portable ASCII");
  }
  const domainBytes = Buffer.from(domain, "ascii");
  const body = typeof payload === "string" ? Buffer.from(payload, "utf8") : Buffer.from(payload);
  const domainLength = Buffer.alloc(4);
  domainLength.writeUInt32BE(domainBytes.length);
  const bodyLength = Buffer.alloc(8);
  bodyLength.writeBigUInt64BE(BigInt(body.length));
  return sha256Bytes(
    Buffer.concat([DOMAIN_FRAME, domainLength, domainBytes, bodyLength, body]),
  );
}

export function assertSha256Digest(value: unknown, label = "digest"): asserts value is Sha256Digest {
  if (typeof value !== "string" || !DIGEST_PATTERN.test(value)) {
    throw new DurableJsonError("INVALID_DIGEST", `${label} must be a full lowercase SHA-256 digest`);
  }
}

class StrictJsonParser {
  private index = 0;
  private readonly text: string;

  constructor(text: string) {
    this.text = text;
  }

  parse(): JsonValue {
    this.skipWhitespace();
    const value = this.parseValue();
    this.skipWhitespace();
    if (this.index !== this.text.length) {
      this.invalidJson("record has trailing content");
    }
    return value;
  }

  private parseValue(): JsonValue {
    const character = this.text[this.index];
    switch (character) {
      case "{":
        return this.parseObject();
      case "[":
        return this.parseArray();
      case '"':
        return this.parseString();
      case "t":
        this.consumeLiteral("true");
        return true;
      case "f":
        this.consumeLiteral("false");
        return false;
      case "n":
        this.consumeLiteral("null");
        return null;
      case "N":
        this.rejectNonFinite("NaN");
      case "I":
        this.rejectNonFinite("Infinity");
      case "-":
        if (this.text.startsWith("-Infinity", this.index)) {
          this.rejectNonFinite("-Infinity");
        }
        return this.parseNumber();
      default:
        if (character !== undefined && character >= "0" && character <= "9") {
          return this.parseNumber();
        }
        this.invalidJson("record contains an unexpected token");
    }
  }

  private parseObject(): { [key: string]: JsonValue } {
    this.index += 1;
    this.skipWhitespace();
    const result: { [key: string]: JsonValue } = {};
    const keys = new Set<string>();
    if (this.consumeIf("}")) {
      return result;
    }
    while (true) {
      if (this.text[this.index] !== '"') {
        this.invalidJson("object key is not a string");
      }
      const key = this.parseString();
      if (keys.has(key)) {
        throw new DurableJsonError("DUPLICATE_KEY", "JSON object contains a duplicate key");
      }
      keys.add(key);
      this.skipWhitespace();
      this.consumeRequired(":", "object key is missing a value separator");
      this.skipWhitespace();
      const value = this.parseValue();
      Object.defineProperty(result, key, {
        configurable: true,
        enumerable: true,
        value,
        writable: true,
      });
      this.skipWhitespace();
      if (this.consumeIf("}")) {
        return result;
      }
      this.consumeRequired(",", "object entries are not comma-separated");
      this.skipWhitespace();
    }
  }

  private parseArray(): JsonValue[] {
    this.index += 1;
    this.skipWhitespace();
    const result: JsonValue[] = [];
    if (this.consumeIf("]")) {
      return result;
    }
    while (true) {
      result.push(this.parseValue());
      this.skipWhitespace();
      if (this.consumeIf("]")) {
        return result;
      }
      this.consumeRequired(",", "array entries are not comma-separated");
      this.skipWhitespace();
    }
  }

  private parseString(): string {
    this.index += 1;
    let result = "";
    while (this.index < this.text.length) {
      const codeUnit = this.text.charCodeAt(this.index);
      if (codeUnit === 0x22) {
        this.index += 1;
        return result;
      }
      if (codeUnit === 0x5c) {
        result += this.parseEscape();
        continue;
      }
      if (codeUnit <= 0x1f) {
        this.invalidJson("string contains an unescaped control character");
      }
      if (isHighSurrogate(codeUnit)) {
        const low = this.text.charCodeAt(this.index + 1);
        if (!isLowSurrogate(low)) {
          this.invalidUnicode();
        }
        result += this.text.slice(this.index, this.index + 2);
        this.index += 2;
        continue;
      }
      if (isLowSurrogate(codeUnit)) {
        this.invalidUnicode();
      }
      result += this.text[this.index];
      this.index += 1;
    }
    this.invalidJson("string is not terminated");
  }

  private parseEscape(): string {
    this.index += 1;
    const escaped = this.text[this.index];
    this.index += 1;
    switch (escaped) {
      case '"':
      case "\\":
      case "/":
        return escaped;
      case "b":
        return "\b";
      case "f":
        return "\f";
      case "n":
        return "\n";
      case "r":
        return "\r";
      case "t":
        return "\t";
      case "u":
        return this.parseUnicodeEscape();
      default:
        this.invalidJson("string contains an invalid escape");
    }
  }

  private parseUnicodeEscape(): string {
    const first = this.readHexCodeUnit();
    if (isHighSurrogate(first)) {
      if (this.text[this.index] !== "\\" || this.text[this.index + 1] !== "u") {
        this.invalidUnicode();
      }
      this.index += 2;
      const second = this.readHexCodeUnit();
      if (!isLowSurrogate(second)) {
        this.invalidUnicode();
      }
      return String.fromCharCode(first, second);
    }
    if (isLowSurrogate(first)) {
      this.invalidUnicode();
    }
    return String.fromCharCode(first);
  }

  private readHexCodeUnit(): number {
    const digits = this.text.slice(this.index, this.index + 4);
    if (digits.length !== 4 || !/^[0-9a-fA-F]{4}$/.test(digits)) {
      this.invalidJson("Unicode escape does not contain four hexadecimal digits");
    }
    this.index += 4;
    return Number.parseInt(digits, 16);
  }

  private parseNumber(): number {
    const start = this.index;
    if (this.consumeIf("-")) {
      if (this.index >= this.text.length) {
        this.invalidJson("number is incomplete");
      }
    }
    if (this.consumeIf("0")) {
      if (isAsciiDigit(this.text[this.index])) {
        this.invalidJson("number contains a leading zero");
      }
    } else {
      if (!isNonZeroAsciiDigit(this.text[this.index])) {
        this.invalidJson("number has no integer component");
      }
      while (isAsciiDigit(this.text[this.index])) {
        this.index += 1;
      }
    }

    let isFractional = false;
    if (this.consumeIf(".")) {
      isFractional = true;
      if (!isAsciiDigit(this.text[this.index])) {
        this.invalidJson("fraction has no digits");
      }
      while (isAsciiDigit(this.text[this.index])) {
        this.index += 1;
      }
    }
    const exponent = this.text[this.index];
    if (exponent === "e" || exponent === "E") {
      isFractional = true;
      this.index += 1;
      const sign = this.text[this.index];
      if (sign === "+" || sign === "-") {
        this.index += 1;
      }
      if (!isAsciiDigit(this.text[this.index])) {
        this.invalidJson("exponent has no digits");
      }
      while (isAsciiDigit(this.text[this.index])) {
        this.index += 1;
      }
    }
    if (isFractional) {
      throw new DurableJsonError(
        "UNSAFE_NUMBER",
        "canonical records do not admit floating-point numbers",
      );
    }
    const token = this.text.slice(start, this.index);
    if (token === "-0") {
      throw new DurableJsonError("UNSAFE_NUMBER", "negative zero is not canonical");
    }
    const integer = BigInt(token);
    if (integer > SAFE_INTEGER_MAX || integer < -SAFE_INTEGER_MAX) {
      throw new DurableJsonError(
        "UNSAFE_NUMBER",
        "integer is outside the interoperable safe range",
      );
    }
    return Number(integer);
  }

  private rejectNonFinite(literal: string): never {
    if (!this.text.startsWith(literal, this.index)) {
      this.invalidJson("record contains an unexpected token");
    }
    throw new DurableJsonError(
      "UNSAFE_NUMBER",
      "non-finite numbers are not valid canonical JSON",
    );
  }

  private consumeLiteral(literal: string): void {
    if (!this.text.startsWith(literal, this.index)) {
      this.invalidJson("record contains an invalid literal");
    }
    this.index += literal.length;
  }

  private consumeIf(character: string): boolean {
    if (this.text[this.index] !== character) {
      return false;
    }
    this.index += 1;
    return true;
  }

  private consumeRequired(character: string, message: string): void {
    if (!this.consumeIf(character)) {
      this.invalidJson(message);
    }
  }

  private skipWhitespace(): void {
    while (true) {
      const character = this.text[this.index];
      if (character !== " " && character !== "\t" && character !== "\r" && character !== "\n") {
        return;
      }
      this.index += 1;
    }
  }

  private invalidJson(message: string): never {
    throw new DurableJsonError("INVALID_JSON", message);
  }

  private invalidUnicode(): never {
    throw new DurableJsonError(
      "INVALID_UNICODE",
      "lone surrogate code points are not interoperable",
    );
  }
}

function compareUtf16(left: string, right: string): number {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function quoteString(value: string): string {
  validateUnicode(value);
  let result = '"';
  for (const character of value) {
    const codePoint = character.codePointAt(0) as number;
    switch (codePoint) {
      case 0x08:
        result += "\\b";
        break;
      case 0x09:
        result += "\\t";
        break;
      case 0x0a:
        result += "\\n";
        break;
      case 0x0c:
        result += "\\f";
        break;
      case 0x0d:
        result += "\\r";
        break;
      case 0x22:
        result += '\\"';
        break;
      case 0x5c:
        result += "\\\\";
        break;
      default:
        if (codePoint <= 0x1f) {
          result += `\\u${codePoint.toString(16).padStart(4, "0")}`;
        } else {
          result += character;
        }
    }
  }
  return `${result}"`;
}

function validateUnicode(value: string): void {
  for (let index = 0; index < value.length; index += 1) {
    const codeUnit = value.charCodeAt(index);
    if (isHighSurrogate(codeUnit)) {
      const low = value.charCodeAt(index + 1);
      if (!isLowSurrogate(low)) {
        throw new DurableJsonError(
          "INVALID_UNICODE",
          "lone surrogate code points are not interoperable",
        );
      }
      index += 1;
    } else if (isLowSurrogate(codeUnit)) {
      throw new DurableJsonError(
        "INVALID_UNICODE",
        "lone surrogate code points are not interoperable",
      );
    }
  }
}

function isAsciiDigit(value: string | undefined): boolean {
  return value !== undefined && value >= "0" && value <= "9";
}

function isNonZeroAsciiDigit(value: string | undefined): boolean {
  return value !== undefined && value >= "1" && value <= "9";
}

function isHighSurrogate(value: number): boolean {
  return value >= 0xd800 && value <= 0xdbff;
}

function isLowSurrogate(value: number): boolean {
  return value >= 0xdc00 && value <= 0xdfff;
}
