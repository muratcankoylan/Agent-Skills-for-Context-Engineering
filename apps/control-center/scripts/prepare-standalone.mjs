import { access, cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const applicationRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const standaloneRoot = resolve(applicationRoot, ".next/standalone");
const standaloneServer = resolve(standaloneRoot, "server.js");
const staticSource = resolve(applicationRoot, ".next/static");
const publicSource = resolve(applicationRoot, "public");
const staticTarget = resolve(standaloneRoot, ".next/static");
const publicTarget = resolve(standaloneRoot, "public");

async function requireBuildPath(path, description) {
  try {
    await access(path);
  } catch {
    throw new Error(
      `Cannot prepare standalone runtime: ${description} is missing at ${path}. Run \"npm run build\" first.`,
    );
  }
}

await Promise.all([
  requireBuildPath(standaloneServer, "standalone server"),
  requireBuildPath(staticSource, "Next.js static assets"),
  requireBuildPath(publicSource, "public assets"),
]);

await mkdir(resolve(standaloneRoot, ".next"), { recursive: true });
await Promise.all([
  rm(staticTarget, { force: true, recursive: true }),
  rm(publicTarget, { force: true, recursive: true }),
]);
await Promise.all([
  cp(staticSource, staticTarget, { recursive: true }),
  cp(publicSource, publicTarget, { recursive: true }),
]);

process.stdout.write("Standalone runtime assets staged.\n");
