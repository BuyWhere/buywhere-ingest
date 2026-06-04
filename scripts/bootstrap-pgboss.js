import dotenv from 'dotenv';
import PgBoss from 'pg-boss';

dotenv.config();

const shouldInitSchema = process.env.BOOTSTRAP_PG_BOSS_SCHEMA === 'true';
if (!shouldInitSchema) {
  console.info('PG Boss schema bootstrap skipped. Set BOOTSTRAP_PG_BOSS_SCHEMA=true to enable.');
  process.exit(0);
}

const requiredEnvironment = process.env.PGBOSS_ALLOWED_ENV;
if (!requiredEnvironment) {
  throw new Error('PGBOSS_ALLOWED_ENV is required when BOOTSTRAP_PG_BOSS_SCHEMA=true.');
}

const isCanonicalTarget =
  process.env.CATALOG_DB_CANONICAL === 'true' &&
  process.env.CATALOG_DB_ENVIRONMENT === requiredEnvironment;

if (!isCanonicalTarget) {
  throw new Error(
    `Refusing to run bootstrap. CATALOG_DB_CANONICAL must be true and CATALOG_DB_ENVIRONMENT must equal ${requiredEnvironment}.`,
  );
}

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) for bootstrap.');
}

const boss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

try {
  await boss.start();
  console.log('Created pg-boss schema/table set in pgboss.* (canonical guard passed).');
} catch (err) {
  console.error('Failed to bootstrap pg-boss schema', err);
  process.exitCode = 1;
} finally {
  await boss.stop();
}
