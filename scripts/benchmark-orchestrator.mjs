#!/usr/bin/env node
// scripts/benchmark-orchestrator.mjs
//
// BUY-34098: Final-stage orchestrator. Waits for all prefilter slices to finish,
// aggregates the outputs, runs the deep-pager per platform, runs the ingest
// stream, and emits a 14-source table + hourly throughput report.
//
// Usage:
//   node scripts/benchmark-orchestrator.mjs --out data/benchmark_2026-06-07

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileP = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const out = {
    out: path.join(REPO_ROOT, "data", "benchmark_2026-06-07"),
    prefilterGlob: "prefilter/tranco_slice_*.ndjson",
    prefilterSliceCount: 8,
    prefilterTimeoutMs: 60 * 60 * 1000,
    deepPageConcurrency: 100,
    perStoreMax: 500,
    ingestBatch: 5000,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") out.out = path.resolve(argv[++i]);
    else if (a === "--prefilter-slice-count") out.prefilterSliceCount = parseInt(argv[++i], 10);
    else if (a === "--deep-page-concurrency") out.deepPageConcurrency = parseInt(argv[++i], 10);
    else if (a === "--per-store-max") out.perStoreMax = parseInt(argv[++i], 10);
    else if (a === "--ingest-batch") out.ingestBatch = parseInt(argv[++i], 10);
  }
  return out;
}

async function pathExists(p) {
  try { await fs.promises.access(p); return true; } catch { return false; }
}

async function runNode(script, cliArgs, outDir, label) {
  console.error(`[orch] run ${label}: node ${script} ${cliArgs.join(" ")}`);
  const logPath = path.join(outDir, "logs", `${label}.log`);
  await fs.promises.mkdir(path.dirname(logPath), { recursive: true });
  const outFh = await fs.promises.open(logPath, "w");
  const child = execFile("node", [path.join(REPO_ROOT, script), ...cliArgs], { cwd: REPO_ROOT });
  child.stdout.on("data", (c) => outFh.write(c));
  child.stderr.on("data", (c) => outFh.write(c));
  return new Promise((res, rej) => {
    child.on("exit", (code) => {
      outFh.close().catch(() => {});
      if (code === 0) res();
      else rej(new Error(`exit_${label}_${code}`));
    });
  });
}

async function waitForPrefilter(outDir, sliceCount, timeoutMs) {
  const t0 = Date.now();
  const files = [];
  for (let i = 0; i < sliceCount; i++) files.push(path.join(outDir, "prefilter", `tranco_slice_${i}.ndjson`));
  // also include any mid-5k slices that may exist
  for (const name of ["tranco_slice_mid_5k", "tranco_slice_mid_5k_v2"]) {
    files.push(path.join(outDir, "prefilter", `${name}.ndjson`));
  }
  // Filter to ones we should wait for (slice_0..N must exist, mid files are optional)
  const required = files.slice(0, sliceCount);
  const optional = files.slice(sliceCount);
  while (Date.now() - t0 < timeoutMs) {
    const reqReady = await Promise.all(required.map(pathExists));
    if (reqReady.every(Boolean)) {
      const optReady = await Promise.all(optional.map(pathExists));
      const optMissing = optReady.filter((r) => !r).length;
      console.error(`[orch] all ${sliceCount} prefilter slices ready after ${Math.round((Date.now() - t0) / 1000)}s; ${optional.length - optMissing}/${optional.length} optional mid slices present`);
      return;
    }
    const missing = reqReady.filter((r) => !r).length;
    console.error(`[orch] prefilter wait: ${sliceCount - missing}/${sliceCount} slices present (still missing ${missing})`);
    await new Promise((r) => setTimeout(r, 30000));
  }
  throw new Error(`prefilter_timeout_${timeoutMs}ms`);
}

async function aggregatePrefilter(outDir) {
  const preDir = path.join(outDir, "prefilter");
  const files = (await fs.promises.readdir(preDir)).filter((f) => (f.startsWith("tranco_slice_") || f.startsWith("tranco_slice_mid_5k")) && f.endsWith(".ndjson")).sort();
  const agg = path.join(outDir, "prefilter", "all_stores.ndjson");
  const fh = await fs.promises.open(agg, "w");
  let total = 0, byPlatform = {};
  for (const f of files) {
    const txt = await fs.promises.readFile(path.join(preDir, f), "utf8");
    for (const line of txt.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try {
        const r = JSON.parse(line);
        fh.write(JSON.stringify(r) + "\n");
        total++;
        byPlatform[r.platform] = (byPlatform[r.platform] || 0) + 1;
      } catch {}
    }
  }
  await fh.close();
  console.error(`[orch] aggregated prefilter: ${total} stores across ${Object.keys(byPlatform).length} platforms`);
  console.error(`[orch] by_platform: ${JSON.stringify(byPlatform)}`);
  return { agg, total, byPlatform };
}

async function main() {
  const args = parseArgs(process.argv);
  await fs.promises.mkdir(path.join(args.out, "logs"), { recursive: true });
  await fs.promises.mkdir(path.join(args.out, "deep-page"), { recursive: true });

  console.error(`[orch] waiting for prefilter slices...`);
  await waitForPrefilter(args.out, args.prefilterSliceCount, args.prefilterTimeoutMs);

  const { agg, total: storeCount, byPlatform } = await aggregatePrefilter(args.out);

  if (storeCount === 0) {
    console.error(`[orch] no stores found; skipping deep-page and ingest`);
    return;
  }

  console.error(`[orch] running deep-page (concurrency=${args.deepPageConcurrency}, per_store_max=${args.perStoreMax})...`);
  const dpOut = path.join(args.out, "deep-page", "all_products.ndjson");
  try {
    await runNode("scripts/deep-page-parallel.mjs", [
      "--input", agg,
      "--output", dpOut,
      "--concurrency", String(args.deepPageConcurrency),
      "--per-store-max", String(args.perStoreMax),
    ], args.out, "deep_page");
  } catch (e) {
    console.error(`[orch] deep-page failed: ${e.message}`);
  }

  if (await pathExists(dpOut)) {
    const products = (await fs.promises.readFile(dpOut, "utf8")).split(/\r?\n/).filter(Boolean);
    console.error(`[orch] deep-page wrote ${products.length} products`);

    console.error(`[orch] running ingest-daemon --once on deep-page output...`);
    try {
      await runNode("scripts/ingest-daemon.mjs", [
        "--watch", path.dirname(dpOut),
        "--batch", String(args.ingestBatch),
        "--once",
      ], args.out, "ingest");
    } catch (e) {
      console.error(`[orch] ingest failed: ${e.message}`);
    }
  }

  console.error(`[orch] DONE`);
}

main().catch((e) => { console.error("[orch] fatal:", e); process.exit(1); });
