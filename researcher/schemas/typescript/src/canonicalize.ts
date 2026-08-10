import { createHash } from "node:crypto";

import { ContractError } from "./errors.js";
import type { JsonValue } from "./json.js";

export const CANONICALIZATION_PROFILE = "jcs-rfc8785-integer-v1" as const;
const SAFE_INTEGER_MAX = Number.MAX_SAFE_INTEGER;

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
    if (!Number.isSafeInteger(value) || Object.is(value, -0) || Math.abs(value) > SAFE_INTEGER_MAX) {
      throw new ContractError(
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
        throw new ContractError("INVALID_JSON", "JSON arrays cannot contain holes");
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
  throw new ContractError("INVALID_JSON", "unsupported JSON value type");
}

export function sha256Bytes(body: string | Uint8Array): string {
  return `sha256:${createHash("sha256").update(body).digest("hex")}`;
}

export function canonicalDigest(value: JsonValue): string {
  return sha256Bytes(Buffer.from(canonicalize(value), "utf8"));
}

function compareUtf16(left: string, right: string): number {
  if (left < right) {
    return -1;
  }
  if (left > right) {
    return 1;
  }
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
    if (codeUnit >= 0xd800 && codeUnit <= 0xdbff) {
      const low = value.charCodeAt(index + 1);
      if (!(low >= 0xdc00 && low <= 0xdfff)) {
        invalidUnicode();
      }
      index += 1;
    } else if (codeUnit >= 0xdc00 && codeUnit <= 0xdfff) {
      invalidUnicode();
    }
  }
}

function invalidUnicode(): never {
  throw new ContractError(
    "INVALID_UNICODE",
    "lone surrogate code points are not interoperable",
  );
}
