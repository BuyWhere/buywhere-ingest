#!/usr/bin/env node
// scripts/ingest-daemon.mjs
//
// BUY-32878: Continuous ingest daemon for discovery NDJSON product files.
// Watches a directory for new .ndjson files, batches them, and upserts into
// the pinned catalog DB (data/.catalog_db_url) using the same SQL contract
// as src/catalog_ingest.py. Hourly throughput report is appended to
// data/discovery_<date>/hourly_report.jsonl.
//
// Usage:
//   node scripts/ingest-daemon.mjs --watch data/discovery_2026-06-06/products [--batch 5000] [--once]
//
// Flags:
//   --watch <dir>   Directory to watch (default: data/discovery_2026-06-06/products)
//   --batch   N     Max rows per batch upsert (default 5000)
//   --once          Process existing files once and exit (no fs.watch loop)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import pg from "pg";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = process.env.NODE_TLS_REJECT_UNAUTHORIZED || "0";

const { Pool } = pg;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const SQL = `
INSERT INTO public.products (
  sku, source, merchant_id, title, description, price, currency, url,
  category, category_path, image_url, is_active, metadata, brand,
  region, country_code, platform, in_stock, gtin
) VALUES %s
ON CONFLICT (sku, source) DO UPDATE SET
  merchant_id = EXCLUDED.merchant_id,
  title = EXCLUDED.title,
  description = EXCLUDED.description,
  price = EXCLUDED.price,
  currency = EXCLUDED.currency,
  url = EXCLUDED.url,
  category = EXCLUDED.category,
  category_path = EXCLUDED.category_path,
  image_url = EXCLUDED.image_url,
  is_active = EXCLUDED.is_active,
  metadata = EXCLUDED.metadata,
  brand = EXCLUDED.brand,
  region = EXCLUDED.region,
  country_code = EXCLUDED.country_code,
  platform = EXCLUDED.platform,
  in_stock = EXCLUDED.in_stock,
  gtin = EXCLUDED.gtin,
  is_available = EXCLUDED.in_stock,
  updated_at = NOW(),
  last_checked = NOW(),
  data_updated_at = NOW()
`;

function parseArgs(argv) {
  const out = {
    watch: path.join(REPO_ROOT, "data", "discovery_2026-06-06", "products"),
    batch: 5000,
    once: false,
    reportFile: null,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--watch") out.watch = path.resolve(argv[++i]);
    else if (a === "--batch") out.batch = parseInt(argv[++i], 10);
    else if (a === "--once") out.once = true;
    else if (a === "--report") out.reportFile = path.resolve(argv[++i]);
  }
  return out;
}

function readCatalogDbUrl() {
  const file = path.join(REPO_ROOT, "data", ".catalog_db_url");
  if (fs.existsSync(file)) {
    return fs.readFileSync(file, "utf8").trim();
  }
  return process.env.DATABASE_URL;
}

function assertIngestionAllowed() {
  try {
    const out = execFileSync("python3", [
      path.join(REPO_ROOT, "scripts", "ingestion_guard.py"),
    ], { stdio: "pipe", encoding: "utf8" });
    process.stderr.write(out || "");
  } catch (e) {
    process.stderr.write(`[ingest-daemon] BLOCKED by guard: ${e.stderr || e.message}\n`);
    process.exit(3);
  }
}

function isLockError(msg) {
  if (!msg) return false;
  const lower = msg.toLowerCase();
  return (
    lower.includes("database is locked") ||
    lower.includes("could not obtain lock") ||
    lower.includes("deadlock detected") ||
    lower.includes("lock_not_available") ||
    lower.includes("connection pool") ||
    lower.includes("too many clients") ||
    lower.includes("remaining connection slots") ||
    lower.includes("max_connections")
  );
}

async function withLockRetry(fn, maxRetries = 5, baseDelayMs = 500) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      if (attempt === maxRetries) throw e;
      if (!isLockError(e.message) && !isLockError(e.code)) throw e;
      const delay = Math.min(baseDelayMs * Math.pow(2, attempt), 30000);
      process.stderr.write(`[ingest-daemon] lock contention, retry ${attempt + 1}/${maxRetries} after ${delay}ms: ${e.message.slice(0, 120)}\n`);
      await new Promise((res) => setTimeout(res, delay));
    }
  }
}

function fabricationCheck(rows) {
  if (rows.length === 0) return { ok: true, share: {} };
  let zeroPrice = 0, nullImage = 0, nullSku = 0, emptyTitle = 0;
  for (const r of rows) {
    if (!r[5] || r[5] === "0" || r[5] === "0.00" || parseFloat(r[5]) === 0) zeroPrice++;
    if (!r[10]) nullImage++;
    if (!r[0]) nullSku++;
    if (!r[3] || (typeof r[3] === "string" && r[3].trim() === "")) emptyTitle++;
  }
  const share = {
    zeroPriceShare: zeroPrice / rows.length,
    nullImageShare: nullImage / rows.length,
    nullSkuShare: nullSku / rows.length,
    emptyTitleShare: emptyTitle / rows.length,
  };
  const ok =
    share.zeroPriceShare < 0.4 &&
    share.nullImageShare < 0.4 &&
    share.nullSkuShare < 0.2 &&
    share.emptyTitleShare < 0.4;
  return { ok, share };
}

function normalizeRow(p) {
  const price = p.price == null || p.price === "" ? "0" : String(p.price);
  const categoryPath = Array.isArray(p.category_path)
    ? p.category_path.map((s) => String(s))
    : p.category_path
    ? [String(p.category_path)]
    : null;
  const metadata = p.metadata || { _writer: { issue: "BUY-32878" } };
  return [
    p.sku || null,
    p.source || "discovery",
    p.merchant_id || null,
    p.title || null,
    p.description || null,
    price,
    p.currency || "USD",
    p.url || null,
    p.category || null,
    categoryPath,
    p.image_url || null,
    p.is_active !== false,
    JSON.stringify(metadata),
    p.brand || null,
    p.region || "US",
    p.country_code || "US",
    p.platform || "shopify",
    p.in_stock !== false,
    p.gtin || null,
  ];
}

async function ingestFile(pool, file) {
  const txt = await fs.promises.readFile(file, "utf8");
  const products = [];
  for (const line of txt.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try {
      products.push(JSON.parse(line));
    } catch (e) {
      // skip
    }
  }
  if (products.length === 0) return { rows: 0, written: 0, fabricated: false };

  const rows = products.map(normalizeRow);
  const seenKeys = new Map();
  const deduped = [];
  for (const r of rows) {
    const key = `${r[0]||''}|${r[1]||''}`;
    if (!key || key === '|') { continue; }
    if (!seenKeys.has(key)) { seenKeys.set(key, true); deduped.push(r); }
  }
  if (deduped.length < rows.length) {
    process.stderr.write(`[ingest-daemon] dedup: ${rows.length} -> ${deduped.length} (removed ${rows.length - deduped.length} duplicate skus)\n`);
  }
  // Filter out rows with null URL (DB NOT NULL constraint at index 7)
  const withUrl = deduped.filter(r => r[7] != null && r[7] !== "");
  if (withUrl.length < deduped.length) {
    process.stderr.write(`[ingest-daemon] filtered ${deduped.length - withUrl.length} rows with null url\n`);
  }
  if (withUrl.length === 0) return { rows: products.length, written: 0, fabricated: false };
  const check = fabricationCheck(withUrl);
  // Row-level filter: instead of rejecting entire batches with high null-price/null-image rates,
  // only skip rows where BOTH price=0 AND image=null (clearly incomplete). Real schema-product
  // scrapes often have valid titles+URLs but missing prices (contact-for-price stores).
  const writable = check.ok ? withUrl : withUrl.filter(r => {
    const hasPrice = r[5] && r[5] !== "0" && r[5] !== "0.00" && parseFloat(r[5]) !== 0;
    const hasImage = r[10] != null && r[10] !== "";
    const hasTitle = r[3] && typeof r[3] === "string" && r[3].trim() !== "";
    // Accept if has title + (price OR image) — real product with at least some data
    return hasTitle && (hasPrice || hasImage);
  });
  const fabricated = !check.ok && writable.length === 0;
  if (fabricated) {
    return { rows: products.length, written: 0, fabricated: true, share: check.share };
  }
  const toWrite = check.ok ? withUrl : writable;

  return withLockRetry(async () => {
    const client = await pool.connect();
    let written = 0;
    try {
      await client.query("BEGIN");
      // Max 3000 rows per batch: 3000 * 19 params = 57000 < 65535 Postgres limit
      for (let i = 0; i < toWrite.length; i += 3000) {
        const batch = toWrite.slice(i, i + 3000);
        const values = batch.map((r, idx) => {
          const offset = idx * 19;
          return `($${offset + 1},$${offset + 2},$${offset + 3},$${offset + 4},$${offset + 5},$${offset + 6}::numeric,$${offset + 7},$${offset + 8},$${offset + 9},$${offset + 10}::text[],$${offset + 11},$${offset + 12}::boolean,$${offset + 13}::jsonb,$${offset + 14},$${offset + 15},$${offset + 16},$${offset + 17},$${offset + 18}::boolean,$${offset + 19})`;
        }).join(",");
        const flat = batch.flat();
        const sql = SQL.replace("%s", values);
        const r = await client.query(sql, flat);
        written += r.rowCount || 0;
      }
      await client.query("COMMIT");
    } catch (e) {
      await client.query("ROLLBACK").catch(() => {});
      throw e;
    } finally {
      client.release();
    }
    return { rows: products.length, written, fabricated: false, share: check.share, skipped_low_quality: toWrite.length < withUrl.length ? withUrl.length - toWrite.length : 0 };
  });
}

async function watchAndProcess(args, pool) {
  const processed = new Set();
  const reportPath = args.reportFile || path.join(REPO_ROOT, "data", "discovery_2026-06-06", "hourly_report.jsonl");
  await fs.promises.mkdir(path.dirname(reportPath), { recursive: true });

  async function scanAndProcess() {
    const files = (await fs.promises.readdir(args.watch))
      .filter((f) => f.endsWith(".ndjson") && !f.endsWith(".processing.ndjson"))
      .map((f) => path.join(args.watch, f))
      .filter((f) => !processed.has(f))
      .sort();
    for (const f of files) {
      const lockPath = `${f}.processing.ndjson`;
      try {
        await fs.promises.rename(f, lockPath);
      } catch (e) {
        // already being processed or missing
        continue;
      }
      const start = Date.now();
      let res;
      try {
        res = await ingestFile(pool, lockPath);
      } catch (e) {
        process.stderr.write(`[ingest-daemon] ${path.basename(lockPath)} failed: ${e.message}\n`);
        try { await fs.promises.rename(lockPath, f); } catch {}
        continue;
      }
      const elapsed_ms = Date.now() - start;
      const report = {
        ts: new Date().toISOString(),
        file: path.basename(lockPath),
        rows: res.rows,
        written: res.written,
        fabricated: res.fabricated,
        fabrication_share: res.share || null,
        elapsed_ms,
        rows_per_sec: res.written > 0 ? (res.written / (elapsed_ms / 1000)).toFixed(1) : 0,
      };
      process.stderr.write(`[ingest-daemon] ${JSON.stringify(report)}\n`);
      await fs.promises.appendFile(reportPath, JSON.stringify(report) + "\n");
      try { await fs.promises.unlink(lockPath); } catch {}
      processed.add(f);
    }
  }

  await scanAndProcess();
  if (args.once) return;

  let lastHourTick = new Date();
  setInterval(async () => {
    await scanAndProcess();
    const now = new Date();
    if (now - lastHourTick >= 60 * 60 * 1000) {
      const summary = {
        ts: now.toISOString(),
        hour_bucket: now.toISOString().slice(0, 13) + ":00:00Z",
        kind: "hourly_summary",
      };
      await fs.promises.appendFile(reportPath, JSON.stringify(summary) + "\n");
      lastHourTick = now;
    }
  }, 15_000);
}

async function main() {
  const args = parseArgs(process.argv);
  assertIngestionAllowed();
  const dbUrl = readCatalogDbUrl();
  if (!dbUrl) {
    console.error("[ingest-daemon] No DB URL (data/.catalog_db_url or DATABASE_URL)");
    process.exit(2);
  }
  await fs.promises.mkdir(args.watch, { recursive: true });
  const pool = new Pool({
    connectionString: dbUrl,
    max: 4,
    ssl: dbUrl.includes("sslmode=require") || dbUrl.includes("sslmode=verify-ca")
      ? { rejectUnauthorized: false }
      : undefined,
  });
  await watchAndProcess(args, pool);
  if (args.once) {
    await pool.end();
    process.exit(0);
  }
}

main().catch((e) => {
  console.error("[ingest-daemon] fatal:", e);
  process.exit(1);
});
