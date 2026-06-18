#!/usr/bin/env node
// scripts/benchmark-14-source.mjs
//
// BUY-34098: Hardened 14-source benchmark runner. Wraps discovery-multi-source.mjs
// with per-source timeouts + a parallel deep-page/ingest pipeline so a single
// slow source (e.g. crt.sh) cannot block the whole cycle.
//
// Usage:
//   node scripts/benchmark-14-source.mjs --out data/benchmark_2026-06-07 --max-per-source 5000

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileP = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const ALL_14 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14];

function parseArgs(argv) {
  const out = {
    out: path.join(REPO_ROOT, "data", "benchmark_2026-06-07"),
    sources: ALL_14.join(","),
    maxPerSource: 5000,
    msTimeoutMs: 90000,   // hard wall-clock cap per multi-source run
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") out.out = path.resolve(argv[++i]);
    else if (a === "--sources") out.sources = argv[++i];
    else if (a === "--max-per-source") out.maxPerSource = parseInt(argv[++i], 10);
  }
  return out;
}

async function withTimeout(promise, ms, label) {
  return await Promise.race([
    promise,
    new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout_${label}_${ms}ms`)), ms)),
  ]);
}

async function runMultiSourceSubset(sources, outDir, maxPerSource) {
  const logFile = path.join(outDir, "logs", `multi_subset_${sources.join("-")}.log`);
  await fs.promises.mkdir(path.dirname(logFile), { recursive: true });
  const stdoutFh = await fs.promises.open(logFile, "w");
  const child = execFile("node", [
    path.join(REPO_ROOT, "scripts", "discovery-multi-source.mjs"),
    "--sources", sources.join(","),
    "--out", outDir,
    "--max-per-source", String(maxPerSource),
  ], { cwd: REPO_ROOT });
  child.stdout.on("data", (c) => stdoutFh.write(c));
  child.stderr.on("data", (c) => stdoutFh.write(c));
  try {
    await withTimeout(new Promise((res, rej) => {
      child.on("exit", (code) => code === 0 ? res() : rej(new Error(`exit_${code}`)));
    }), 90000, `multi_${sources.join("-")}`);
  } catch (e) {
    try { child.kill("SIGKILL"); } catch {}
    stdoutFh.write(`\n[benchmark] KILLED: ${e.message}\n`);
  }
  await stdoutFh.close();
  return { sources, log: logFile };
}

async function readSourceCounts(outDir) {
  const rawDir = path.join(outDir, "raw");
  if (!fs.existsSync(rawDir)) return {};
  const counts = {};
  for (const sid of ALL_14) {
    const f = path.join(rawDir, `source_${sid}.ndjson`);
    if (fs.existsSync(f)) {
      const lines = (await fs.promises.readFile(f, "utf8")).split(/\r?\n/).filter(Boolean);
      counts[sid] = lines.length;
    } else {
      counts[sid] = 0;
    }
  }
  return counts;
}

async function main() {
  const args = parseArgs(process.argv);
  await fs.promises.mkdir(path.join(args.out, "logs"), { recursive: true });

  const startCounts = await readSourceCounts(args.out);
  console.error(`[benchmark] starting; existing counts: ${JSON.stringify(startCounts)}`);

  // Group sources into 3 sub-runs to spread the 90s wall-clock budget:
  //   group A: 3,4,9,10 (tranco + CDX + affiliate + schema)  — fast, network-light
  //   group B: 1,2,5,6,7,8 (deferred/empty stubs)              — instant
  //   group C: 11,12,13,14 (CT logs + GitHub + DNS + Amazon)   — slow/cranky
  // Run all three groups in parallel so a slow group can't block a fast one.
  const groups = [
    [3, 4, 9, 10],
    [1, 2, 5, 6, 7, 8],
    [11, 12, 13, 14],
  ];
  const results = await Promise.all(groups.map((g) => runMultiSourceSubset(g, args.out, args.maxPerSource)));
  for (const r of results) console.error(`[benchmark] group done: sources=${r.sources.join(",")} log=${r.log}`);

  const endCounts = await readSourceCounts(args.out);
  console.error(`[benchmark] final counts: ${JSON.stringify(endCounts)}`);

  const deltas = {};
  for (const sid of ALL_14) {
    deltas[sid] = (endCounts[sid] || 0) - (startCounts[sid] || 0);
  }
  console.error(`[benchmark] deltas: ${JSON.stringify(deltas)}`);

  const summary = {
    finished_at: new Date().toISOString(),
    out: args.out,
    counts: endCounts,
    deltas,
  };
  await fs.promises.writeFile(
    path.join(args.out, "logs", "benchmark_summary.json"),
    JSON.stringify(summary, null, 2),
  );
  console.error(`[benchmark] DONE`);
}

main().catch((e) => {
  console.error("[benchmark] fatal:", e);
  process.exit(1);
});
