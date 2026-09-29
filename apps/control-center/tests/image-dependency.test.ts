import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const nextRequire = createRequire(require.resolve("next/package.json"));

test("the image dependency lock retains the GHSA-rgj7-g3m4-5g8c patch", async () => {
  // Review this explicit security pin together with every native package on upgrade.
  const manifest = JSON.parse(
    await readFile(new URL("../package.json", import.meta.url), "utf8"),
  );
  const lock = JSON.parse(
    await readFile(new URL("../package-lock.json", import.meta.url), "utf8"),
  );
  assert.equal(manifest.overrides?.sharp, "0.35.4");
  const entries = Object.entries(lock.packages) as [string, { version?: string }][];
  const sharpEntries = entries.filter(([path]) => path.endsWith("/sharp"));
  const nativeEntries = entries.filter(([path]) => path.includes("/@img/sharp-"));
  assert.ok(sharpEntries.length > 0);
  assert.ok(nativeEntries.length > 0);
  for (const [path, record] of [...sharpEntries, ...nativeEntries]) {
    const expected = path.includes("/@img/sharp-libvips-") ? "1.3.3" : "0.35.4";
    assert.equal(record.version, expected, path);
  }
  assert.equal(nextRequire("sharp").versions.sharp, "0.35.4");
});

test("Next image conversion uses patched native libraries and retains its decode guard", async () => {
  const sharp: import("sharp").SharpConstructor = nextRequire("sharp");
  assert.equal(sharp.versions.sharp, "0.35.4");
  assert.equal(sharp.versions.heif, "1.23.2");
  const input = { create: { width: 8, height: 6, channels: 3 as const,
    background: { r: 32, g: 96, b: 160 } } };
  const png = await sharp(input).png().toBuffer();
  const avif = await sharp(input).avif({ effort: 0 }).toBuffer();
  assert.equal((await sharp(avif).metadata()).format, "heif");
  const { getSharp, optimizeImage }: typeof import("next/dist/server/image-optimizer") =
    nextRequire("next/dist/server/image-optimizer");
  const guarded = getSharp(1, false);
  assert.equal(guarded, sharp);
  const output = await optimizeImage({ buffer: png, contentType: "image/webp",
    quality: 75, width: 4, height: 3, concurrency: 1, operationCache: false,
    limitInputPixels: 64, sequentialRead: true, timeoutInSeconds: 5 });
  const metadata = await guarded(output).metadata();
  assert.equal(metadata.format, "webp");
  assert.equal(metadata.width, 4);
  assert.equal(metadata.height, 3);
  await assert.rejects(guarded(avif).metadata(), /unsupported image format|blocked|not allowed/i);
});
