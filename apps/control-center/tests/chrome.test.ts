import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createElement } from "react";
import * as jsxRuntime from "react/jsx-runtime";
import { renderToStaticMarkup } from "react-dom/server";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

// Node's type-strip test runner cannot execute JSX. Transpile only the shell,
// stub its route boundary, then render the actual component with React.
async function renderChrome(pathname: string) {
  const source = await readFile(new URL("../components/chrome.tsx", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } });
  const module = { exports: {} as Record<string, (props: { children: ReturnType<typeof createElement> }) => ReturnType<typeof createElement>> };
  const require = (name: string) => {
    if (name === "react/jsx-runtime") return jsxRuntime;
    if (name === "next/navigation") return { usePathname: () => pathname };
    if (name === "next/link") return { default: (props: object) => createElement("a", props) };
    if (name === "./primary-navigation.tsx") return { PrimaryNavigation: () => null };
    throw new Error("Unexpected shell dependency");
  };
  vm.runInNewContext(outputText, { module, exports: module.exports, require }, { timeout: 1000 });
  return renderToStaticMarkup(createElement(module.exports.AppChrome, { children: createElement("p", null, "Page content") }));
}

test("service shell labels real read-only status without fabricated fixture banners", async () => {
  const html = await renderChrome("/service");
  assert.match(html, /Standalone research service/);
  assert.match(html, /Research service status/);
  assert.match(html, /page issues no commands/);
  assert.match(html, /reservations, not verified paid requests/);
  assert.doesNotMatch(html, /Fabricated fixture|Discardable design experiment|fixture adapter|>Fixture</);
});

test("observation and fixture shell boundaries remain distinct", async () => {
  const observations = await renderChrome("/observations");
  assert.match(observations, /Local observation pilot/);
  assert.doesNotMatch(observations, /Standalone research service|>Fixture</);
  const fixtures = await renderChrome("/review");
  assert.match(fixtures, /Fabricated fixture data/);
  assert.match(fixtures, /Discardable design experiment/);
  assert.match(fixtures, />Fixture</);
});
