import fs from "node:fs";
import pg from "pg";
import { execFileSync } from "node:child_process";
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
const { Pool } = pg;

const dbUrl = fs.readFileSync("data/.catalog_db_url","utf8").trim();
const pool = new Pool({ connectionString: dbUrl, max: 4, ssl: { rejectUnauthorized: false } });

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

function normalizeRow(p) {
  const price = p.price == null || p.price === "" ? "0" : String(p.price);
  const categoryPath = Array.isArray(p.category_path) ? p.category_path.map((s) => String(s)) : p.category_path ? [String(p.category_path)] : null;
  const metadata = p.metadata || { _writer: { issue: "BUY-34098" } };
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

const txt = fs.readFileSync("data/benchmark_2026-06-07/deep-page/curated_products.ndjson", "utf8");
const products = [];
for (const line of txt.split(/\r?\n/)) {
  if (!line.trim()) continue;
  try { products.push(JSON.parse(line)); } catch {}
}
console.log(`Loaded ${products.length} products`);

// Dedupe
const seenKeys = new Map();
const deduped = [];
for (const p of products) {
  const key = `${p.sku||''}|${p.source||''}`;
  if (!key || key === '|') continue;
  if (!seenKeys.has(key)) { seenKeys.set(key, true); deduped.push(p); }
}
console.log(`Dedup: ${products.length} -> ${deduped.length}`);

const rows = deduped.map(normalizeRow);
const BATCH = 500;  // small batch to avoid the 29464 error
let totalWritten = 0;
let batchNum = 0;
for (let i = 0; i < rows.length; i += BATCH) {
  batchNum++;
  const batch = rows.slice(i, i + BATCH);
  const values = batch.map((r, idx) => {
    const offset = idx * 19;
    return `($${offset+1},$${offset+2},$${offset+3},$${offset+4},$${offset+5},$${offset+6}::numeric,$${offset+7},$${offset+8},$${offset+9},$${offset+10}::text[],$${offset+11},$${offset+12}::boolean,$${offset+13}::jsonb,$${offset+14},$${offset+15},$${offset+16},$${offset+17},$${offset+18}::boolean,$${offset+19})`;
  }).join(",");
  const flat = batch.flat();
  const sql = SQL.replace("%s", values);
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const r = await client.query(sql, flat);
    await client.query("COMMIT");
    totalWritten += r.rowCount || 0;
    if (batchNum % 2 === 0 || batchNum === Math.ceil(rows.length / BATCH)) {
      console.log(`Batch ${batchNum}/${Math.ceil(rows.length / BATCH)}: ${r.rowCount} written (total ${totalWritten})`);
    }
  } catch (e) {
    await client.query("ROLLBACK").catch(() => {});
    console.error(`Batch ${batchNum} failed: ${e.message}`);
    // Try batch of 100
    for (let j = 0; j < batch.length; j += 100) {
      const subBatch = batch.slice(j, j + 100);
      try {
        const subValues = subBatch.map((r, idx) => {
          const offset = idx * 19;
          return `($${offset+1},$${offset+2},$${offset+3},$${offset+4},$${offset+5},$${offset+6}::numeric,$${offset+7},$${offset+8},$${offset+9},$${offset+10}::text[],$${offset+11},$${offset+12}::boolean,$${offset+13}::jsonb,$${offset+14},$${offset+15},$${offset+16},$${offset+17},$${offset+18}::boolean,$${offset+19})`;
        }).join(",");
        const subFlat = subBatch.flat();
        const subSql = SQL.replace("%s", subValues);
        const subR = await client.query(subSql, subFlat);
        totalWritten += subR.rowCount || 0;
      } catch (e2) {
        console.error(`Sub-batch ${batchNum}.${j/100+1} failed: ${e2.message}`);
      }
    }
  } finally {
    client.release();
  }
}
console.log(`Total written: ${totalWritten}`);
await pool.end();
