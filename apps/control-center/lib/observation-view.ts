export const observationSchema = "local-research-observation-view/v1";
export const observationMaxBytes = 256 * 1024;
export const observationMaxAgeSeconds = 2 * 60 * 60;

export interface ObservationRun {
  readonly run_id: string;
  readonly query: string;
  readonly status: "awaiting_researcher" | "partial" | "failed";
  readonly observed_at: string;
  readonly source_count: number;
  readonly capture_count: number;
  readonly context_bytes: number;
  readonly model_calls: 0;
  readonly report_digest: string;
  readonly blockers: readonly string[];
}

export interface ObservationView {
  readonly schema: typeof observationSchema;
  readonly authority: "none";
  readonly production_ready: false;
  readonly generated_at: string;
  readonly runs: readonly ObservationRun[];
}

export interface ObservationReadResult {
  readonly schema: "local-research-observation-read/v1";
  readonly authority: "none";
  readonly production_ready: false;
  readonly state: "disabled" | "missing" | "invalid" | "current" | "stale";
  readonly reason: string;
  readonly checked_at: string;
  readonly max_age_seconds: number;
  readonly data: ObservationView | null;
}

/** A bounded JSON parser preserves duplicate-key errors lost by JSON.parse. */
export function strictJson(text: string): unknown {
  let index = 0;
  let nodes = 0;
  function whitespace() {
    while (index < text.length && /[\t\n\r ]/.test(text[index])) index++;
  }
  function string(): string {
    const start = index++;
    while (index < text.length) {
      const character = text[index++];
      if (character === "\\") index++;
      else if (character === '"') return JSON.parse(text.slice(start, index)) as string;
    }
    throw new Error("invalid_json");
  }
  function value(depth: number): unknown {
    if (depth > 8 || ++nodes > 10000) throw new Error("json_bounds");
    whitespace();
    const character = text[index];
    if (character === '"') return string();
    if (character === "{" || character === "[") {
      const object = character === "{";
      const close = object ? "}" : "]";
      index++;
      whitespace();
      const record: Record<string, unknown> = Object.create(null);
      const array: unknown[] = [];
      const keys = new Set<string>();
      if (text[index] !== close) {
        while (true) {
          whitespace();
          if (object) {
            if (text[index] !== '"') throw new Error("invalid_json");
            const key = string();
            if (keys.has(key)) throw new Error("duplicate_json_key");
            keys.add(key);
            whitespace();
            if (text[index++] !== ":") throw new Error("invalid_json");
            record[key] = value(depth + 1);
          } else array.push(value(depth + 1));
          whitespace();
          if (text[index] !== ",") break;
          index++;
        }
      }
      if (text[index++] !== close) throw new Error("invalid_json");
      return object ? record : array;
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(index));
    if (token === null) throw new Error("invalid_json");
    index += token[0].length;
    return JSON.parse(token[0]) as unknown;
  }
  const parsed = value(0);
  whitespace();
  if (index !== text.length) throw new Error("invalid_json");
  return parsed;
}

function exactObject(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid_object");
  const record = value as Record<string, unknown>;
  const actual = Object.keys(record);
  if (actual.length !== keys.length || actual.some((key) => !keys.includes(key))) throw new Error("unknown_or_missing_field");
  return record;
}

function boundedText(value: unknown, maximum = 2048): string {
  if (typeof value !== "string" || value.trim().length === 0 || new TextEncoder().encode(value).length > maximum || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)) {
    throw new Error("invalid_text");
  }
  // Lone surrogates would otherwise be silently replaced during serialization.
  if (new TextDecoder("utf-8", { fatal: true }).decode(new TextEncoder().encode(value)) !== value) throw new Error("invalid_unicode");
  return value;
}

function timestamp(value: unknown): number {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) throw new Error("invalid_timestamp");
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString().replace(".000Z", "Z") !== value) throw new Error("invalid_timestamp");
  return milliseconds;
}

function count(value: unknown, maximum: number): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0 || value > maximum) throw new Error("invalid_count");
  return value;
}

export function parseObservationView(text: string, now: number): ObservationView {
  if (new TextEncoder().encode(text).length > observationMaxBytes || !Number.isFinite(now)) throw new Error("invalid_bounds");
  const root = exactObject(strictJson(text), ["schema", "authority", "production_ready", "generated_at", "runs"]);
  if (root.schema !== observationSchema || root.authority !== "none" || root.production_ready !== false) throw new Error("invalid_authority");
  const generated = timestamp(root.generated_at);
  if (generated > now + 60000) throw new Error("future_timestamp");
  if (!Array.isArray(root.runs) || root.runs.length > 50) throw new Error("invalid_runs");
  const identities = new Set<string>();
  const runs = root.runs.map((item): ObservationRun => {
    const run = exactObject(item, ["run_id", "query", "status", "observed_at", "source_count", "capture_count", "context_bytes", "model_calls", "report_digest", "blockers"]);
    if (typeof run.run_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(run.run_id) || identities.has(run.run_id)) throw new Error("invalid_run_id");
    identities.add(run.run_id);
    if (run.status !== "awaiting_researcher" && run.status !== "partial" && run.status !== "failed") throw new Error("invalid_status");
    const observed = timestamp(run.observed_at);
    if (observed > now + 60000 || observed > generated + 60000) throw new Error("future_timestamp");
    if (run.model_calls !== 0 || typeof run.report_digest !== "string" || !/^sha256:[0-9a-f]{64}$/.test(run.report_digest)) throw new Error("invalid_evidence_boundary");
    if (!Array.isArray(run.blockers) || run.blockers.length > 50) throw new Error("invalid_blockers");
    return {
      run_id: run.run_id, query: boundedText(run.query), status: run.status,
      observed_at: run.observed_at as string, source_count: count(run.source_count, 1000),
      capture_count: count(run.capture_count, 1000), context_bytes: count(run.context_bytes, Number.MAX_SAFE_INTEGER),
      model_calls: 0, report_digest: run.report_digest, blockers: run.blockers.map((value) => boundedText(value)),
    };
  });
  return { schema: observationSchema, authority: "none", production_ready: false, generated_at: root.generated_at as string, runs };
}

export function isLoopbackHost(value: string | null | undefined): boolean {
  if (typeof value !== "string") return false;
  const match = /^127\.0\.0\.1(?::([1-9]\d{0,4}))?$/.exec(value);
  return match !== null && (match[1] === undefined || Number(match[1]) <= 65535);
}
