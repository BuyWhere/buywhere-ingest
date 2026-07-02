// src/queues.js
// Single source of truth for pg-boss queue names consumed by the worker.
//
// BUY-59728: extracted from src/worker.js to fix a temporal-dead-zone crash.
// The previous layout declared some queue-name constants (DISCOVER_CC_QUEUE,
// DISCOVER_TRANCO_QUEUE, DISCOVER_SITEMAP_QUEUE, LANE_QUEUES) several
// hundred lines BELOW the top-level `await ensureQueuePartitions(pgBoss)`
// call. Function declarations are hoisted, but `const` initialisers are
// not — so the bootstrap call at line ~93 read the bindings inside their
// TDZ and threw `ReferenceError: Cannot access 'DISCOVER_CC_QUEUE' before
// initialization` on every fresh container, crash-looping the worker
// healthcheck and stranding 850 jobs in pgboss.job for 4 days.
//
// Keeping all queue-name constants in this module, imported at the top of
// worker.js, makes the TDZ impossible to reintroduce by re-adding a
// `await ensureQueuePartitions(...)` anywhere in the file.

import { LANE_ROLES } from './laneRunner.js';

// BUY-33060 / BUY-34833: Shopify scraping queues (page-1 and deep).
export const PAGE1_QUEUE = 'scrape.shopify';
export const DEEP_QUEUE = 'scrape.shopify.deep';

// BUY-34834: WooCommerce deep-page queue.
export const WC_DEEP_QUEUE = 'scrape.woocommerce.deep';

// BUY-34835: Common Crawl discovery queue.
export const DISCOVER_CC_QUEUE = 'discover.cc';

// BUY-34836: Tranco non-Shopify platform discovery queue.
export const DISCOVER_TRANCO_QUEUE = 'discover.tranco';

// BUY-34837: Sitemap-driven merchant discovery queue.
export const DISCOVER_SITEMAP_QUEUE = 'discover.sitemap';

// BUY-34838: per-role lane queues for the buy30620 hunt/hunt2/stock/crate/scout lanes.
export const LANE_QUEUE_PREFIX = 'scrape.shopify.lane.';
export const LANE_QUEUES = LANE_ROLES.map((role) => `${LANE_QUEUE_PREFIX}${role}`);
