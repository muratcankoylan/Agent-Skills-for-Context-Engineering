import { ContractError } from "./errors.js";

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

const SAFE_INTEGER_MAX = 9_007_199_254_740_991n;

/** Parse the integer-only I-JSON profile without silent key or number coercion. */
export function parseJsonStrict(text: string): JsonValue {
  return new StrictJsonParser(text).parse();
}

class StrictJsonParser {
  private index = 0;

  constructor(private readonly text: string) {}

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
        throw new ContractError("DUPLICATE_KEY", "JSON object contains a duplicate key");
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
      throw new ContractError(
        "UNSAFE_NUMBER",
        "canonical records do not admit floating-point numbers",
      );
    }
    const token = this.text.slice(start, this.index);
    if (token === "-0") {
      throw new ContractError("UNSAFE_NUMBER", "negative zero is not canonical");
    }
    const integer = BigInt(token);
    if (integer > SAFE_INTEGER_MAX || integer < -SAFE_INTEGER_MAX) {
      throw new ContractError(
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
    throw new ContractError(
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
    throw new ContractError("INVALID_JSON", message);
  }

  private invalidUnicode(): never {
    throw new ContractError(
      "INVALID_UNICODE",
      "lone surrogate code points are not interoperable",
    );
  }
}

function isAsciiDigit(character: string | undefined): boolean {
  return character !== undefined && character >= "0" && character <= "9";
}

function isNonZeroAsciiDigit(character: string | undefined): boolean {
  return character !== undefined && character >= "1" && character <= "9";
}

function isHighSurrogate(codeUnit: number): boolean {
  return codeUnit >= 0xd800 && codeUnit <= 0xdbff;
}

function isLowSurrogate(codeUnit: number): boolean {
  return codeUnit >= 0xdc00 && codeUnit <= 0xdfff;
}
