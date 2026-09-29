// Node-only module. Never import this file into a Client Component.
import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";
import { dirname, isAbsolute, normalize, parse } from "node:path";
import {
  isLoopbackHost, observationMaxAgeSeconds, observationMaxBytes, parseObservationView,
} from "./observation-view.ts";
import type { ObservationReadResult } from "./observation-view.ts";

export async function readObservationView({
  environment = process.env,
  requestHost,
  now = Date.now(),
}: {
  readonly environment?: Readonly<Record<string, string | undefined>>;
  readonly requestHost: string | null;
  readonly now?: number;
}): Promise<ObservationReadResult> {
  const base = {
    schema: "local-research-observation-read/v1" as const,
    authority: "none" as const, production_ready: false as const,
    checked_at: new Date(now).toISOString(), max_age_seconds: observationMaxAgeSeconds,
  };
  const unavailable = (state: "disabled" | "missing" | "invalid", reason: string): ObservationReadResult => ({ ...base, state, reason, data: null });
  if (environment.RESEARCH_OBSERVATIONS_ENABLED !== "1") return unavailable("disabled", "local_observations_not_enabled");
  if (environment.HOSTNAME !== "127.0.0.1" || !isLoopbackHost(requestHost)) return unavailable("disabled", "loopback_required");
  const configured = environment.RESEARCH_OBSERVATION_FILE;
  if (configured === undefined || configured === "") return unavailable("missing", "observation_file_not_configured");
  if (!isAbsolute(configured) || configured.includes("\0") || normalize(configured) !== configured) return unavailable("invalid", "unsafe_observation_file");
  try {
    // Reject ancestor aliases as well as a leaf symlink. This is a local pilot
    // under one OS owner, not a hostile shared-directory or authentication boundary.
    let parent = dirname(configured);
    while (true) {
      const metadata = await lstat(parent);
      if (!metadata.isDirectory() || metadata.isSymbolicLink()) return unavailable("invalid", "unsafe_observation_file");
      if (parent === parse(parent).root) break;
      parent = dirname(parent);
    }
    const handle = await open(configured, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    try {
      const before = await handle.stat();
      if (!before.isFile() || before.nlink !== 1 || before.size > observationMaxBytes) return unavailable("invalid", "unsafe_or_oversized_observation_file");
      const buffer = Buffer.alloc(observationMaxBytes + 1);
      let bytes = 0;
      while (bytes < buffer.length) {
        const result = await handle.read(buffer, bytes, buffer.length - bytes, bytes);
        if (result.bytesRead === 0) break;
        bytes += result.bytesRead;
      }
      const after = await handle.stat();
      if (bytes > observationMaxBytes || bytes !== before.size || after.size !== before.size || after.mtimeMs !== before.mtimeMs || after.ctimeMs !== before.ctimeMs) return unavailable("invalid", "observation_changed_during_read");
      const text = new TextDecoder("utf-8", { fatal: true }).decode(buffer.subarray(0, bytes));
      const data = parseObservationView(text, now);
      const stale = now - Date.parse(data.generated_at) > observationMaxAgeSeconds * 1000;
      return { ...base, state: stale ? "stale" : "current", reason: stale ? "observation_view_expired" : "local_observation_read", data };
    } finally {
      await handle.close();
    }
  } catch (error) {
    if (error instanceof Error && "code" in error && error.code === "ENOENT") return unavailable("missing", "observation_file_missing");
    // No exception messages or private locators cross the response boundary.
    return unavailable("invalid", "observation_file_invalid");
  }
}
