/** No dotenv loading, credential lookup, or ambient provider construction. */
export const config = { openai: { model: 'unconfigured' } } as const;

/** @deprecated Construct and inject a bounded JudgeRuntime explicitly. */
export function validateConfig(): void {
  throw new Error('Automatic live execution is disabled. See README for explicit bounded runtime setup.');
}
