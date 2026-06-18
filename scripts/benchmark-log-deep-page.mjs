#!/usr/bin/env node
// scripts/benchmark-log-deep-page.mjs
//
// BUY-34098: Extracts passed domains from prefilter log files and runs deep-page
// on the union. Used to make progress while the prefilter is still running.

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
    concurrency: 50,
    perStoreMax: 250,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") out.out = path.resolve(argv[++i]);
    else if (a === "--concurrency") out.concurrency = parseInt(argv[++i], 10);
    else if (a === "--per-store-max") out.perStoreMax = parseInt(argv[++i], 10);
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  const logsDir = path.join(args.out, "logs");
  const preDir = path.join(args.out, "prefilter");
  const dpDir = path.join(args.out, "deep-page");
  fs.mkdirSync(dpDir, { recursive: true });
  const logFiles = (await fs.promises.readdir(logsDir)).filter((f) => f.startsWith("prefilter_tranco_") && f.endsWith(".log"));
  // Just a placeholder; we don't have the actual passed domains in logs.
  // Skip — the partial deep-page would need domain->platform mapping.
  // For now, just report counts.
  let totalPassed = 0;
  for (const lf of logFiles) {
    const txt = await fs.promises.readFile(path.join(logsDir, lf), "utf8");
    const lines = txt.split(/\r?\n/).filter(Boolean);
    if (lines.length === 0) continue;
    const last = lines[lines.length - 1];
    const m = last.match(/checked=\d+\/\d+ passed=(\d+)/);
    if (m) {
      totalPassed += parseInt(m[1], 10);
    }
  }
  console.error(`[log-dp] in-flight passed total: ${totalPassed} (across ${logFiles.length} prefilter logs)`);
  console.error(`[log-dp] no incremental deep-page — the prefilter output is only written at the end`);
}

main().catch((e) => { console.error("[log-dp] fatal:", e); process.exit(1); });
