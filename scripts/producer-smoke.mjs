import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';

dotenv.config();

const url = process.env.DATABASE_URL;
if (!url) throw new Error('DATABASE_URL not set');

const pgBoss = new PgBoss({ connectionString: url, schema: 'pgboss' });
const db = new pg.Pool({ connectionString: url, max: 2 });

async function findCandidates(limit) {
  const r = await db.query(
    `SELECT id, name, source, country, onboarding_stage
       FROM merchants
      WHERE source = 'shopify'
        AND onboarding_stage IN ('discovered', 'interested', 'backfilled_orphan')
        AND country = ANY($1::text[])
      ORDER BY created_at ASC
      LIMIT $2`,
    [['US','SG'], limit]
  );
  return r.rows;
}

async function main() {
  console.log('[smoke] starting pgboss.start() against live DB...');
  await pgBoss.start();
  console.log('[smoke] pgboss started. ensuring queue exists...');
  try { await pgBoss.createQueue('scrape.shopify'); console.log('[smoke] queue ensured.'); }
  catch (e) { console.log('[smoke] createQueue note:', e.message); }

  const candidates = await findCandidates(3);
  console.log(`[smoke] found ${candidates.length} candidates:`);
  for (const c of candidates) {
    console.log(`  - ${c.id} | ${c.onboarding_stage} | ${c.country}`);
  }

  if (candidates.length > 0) {
    const m = candidates[0];
    const source = `shopify_${m.id.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
    const jobId = await pgBoss.send('scrape.shopify', {
      merchantId: m.id, domain: m.id, source, country: m.country, onboardingStage: m.onboarding_stage,
      enqueuedAt: new Date().toISOString(),
    }, { singletonKey: m.id, singletonHours: 6, retryLimit: 2, expireInHours: 23 });
    console.log(`[smoke] enqueued ONE job for ${m.id}, jobId=${jobId}`);
  }

  console.log('[smoke] done.');
  await pgBoss.stop();
  await db.end();
}

main().catch(async (e) => {
  console.error('[smoke] error:', e);
  process.exitCode = 1;
  try { await pgBoss.stop(); } catch {}
  try { await db.end(); } catch {}
});
