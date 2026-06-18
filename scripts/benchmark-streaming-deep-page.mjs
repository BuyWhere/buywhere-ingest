#!/usr/bin/env node
// scripts/benchmark-streaming-deep-page.mjs
//
// BUY-34098: Streaming companion to benchmark-orchestrator. Watches for new
// prefilter output files (slice_0..7, mid_5k*, e1*, e2*) and runs the
// deep-pager on each as it appears. Output is written to a single combined
// NDJSON; ingest stream picks it up.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const out = {
    out: path.join(REPO_ROOT, "data", "benchmark_2026-06-07"),
    pollMs: 20000,
    deepPageConcurrency: 50,
    perStoreMax: 500,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") out.out = path.resolve(argv[++i]);
    else if (a === "--poll-ms") out.pollMs = parseInt(argv[++i], 10);
    else if (a === "--deep-page-concurrency") out.deepPageConcurrency = parseInt(argv[++i], 10);
    else if (a === "--per-store-max") out.perStoreMax = parseInt(argv[++i], 10);
  }
  return out;
}

function listPrefilterFiles(preDir) {
  if (!fs.existsSync(preDir)) return [];
  return (fs.readdirSync(preDir))
    .filter((f) => (f.startsWith("tranco_slice_") || f.startsWith("tranco_mid_5k")) && f.endsWith(".ndjson"))
    .filter((f) => !f.includes("all_stores")) // exclude the aggregated file
    .sort();
}

async function runDeepPage(input, output, concurrency, perStoreMax) {
  return new Promise((res, rej) => {
    const child = execFile("node", [
      path.join(REPO_ROOT, "scripts", "deep-page-parallel.mjs"),
      "--input", input,
      "--output", output,
      "--concurrency", String(concurrency),
      "--per-store-max", String(perStoreMax),
    ], { cwd: REPO_ROOT });
    let stderr = "";
    child.stdout.on("data", (c) => process.stderr.write(`[stream-dp] ${c}`));
    child.stderr.on("data", (c) => { stderr += c.toString(); process.stderr.write(`[stream-dp] ${c}`); });
    child.on("exit", (code) => {
      if (code === 0) res();
      else rej(new Error(`deep_page_failed_${code}: ${stderr.slice(-500)}`));
    });
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const preDir = path.join(args.out, "prefilter");
  const dpDir = path.join(args.out, "deep-page");
  fs.mkdirSync(dpDir, { recursive: true });
  const stateFile = path.join(args.out, "deep-page", ".streamed.json");
  let state = {};
  if (fs.existsSync(stateFile)) state = JSON.parse(fs.readFileSync(stateFile, "utf8"));

  console.error(`[stream-dp] watching ${preDir} for new prefilter outputs...`);
  while (true) {
    const files = listPrefilterFiles(preDir);
    const pending = files.filter((f) => !state[f]);
    if (pending.length === 0) {
      await new Promise((r) => setTimeout(r, args.pollMs));
      continue;
    }
    for (const f of pending) {
      const input = path.join(preDir, f);
      const outFile = path.join(dpDir, f.replace(/\.ndjson$/, "_products.ndjson"));
      const t0 = Date.now();
      try {
        // Build a single-line NDJSON input (prefilter is already NDJSON)
        await runDeepPage(input, outFile, args.deepPageConcurrency, args.perStoreMax);
        const productCount = fs.existsSync(outFile)
          ? fs.readFileSync(outFile, "utf8").split(/\r?\n/).filter(Boolean).length
          : 0;
        state[f] = { done_at: new Date().toISOString(), elapsed_ms: Date.now() - t0, products: productCount, out: outFile };
        console.error(`[stream-dp] done: ${f} products=${productCount} elapsed_ms=${Date.now() - t0}`);
      } catch (e) {
        state[f] = { done_at: new Date().toISOString(), error: e.message };
        console.error(`[stream-dp] failed: ${f} ${e.message}`);
      }
      fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
    }
  }
}

main().catch((e) => { console.error("[stream-dp] fatal:", e); process.exit(1); });
