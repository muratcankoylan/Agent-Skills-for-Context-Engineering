export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@cursor/sdk" || specifier.startsWith("@cursor/sdk/")) {
    throw new Error("SDK_IMPORT_FORBIDDEN_DURING_DRY_RUN");
  }
  return nextResolve(specifier, context);
}
