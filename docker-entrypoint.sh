#!/bin/sh
# Select which process to run based on SERVICE_ROLE env var.
# Default to "server" so the old buywhere-ingest (cron producer) keeps
# its pre-BUY-33687 behavior unless explicitly overridden.
#
# BUY-34834 / BUY-34835 / BUY-34837: producer-wc, producer-cc, and
# producer-sitemap are the dedicated SERVICE_ROLE values for the
# WooCommerce deep-page producer, Common Crawl discovery producer, and
# sitemap-driven merchant discovery producer respectively. They run the
# same `node src/<file>.js` shape so a single image covers all roles
# (server, worker, producer, producer-wc, producer-cc, producer-tranco,
# producer-sitemap).
#
# Scheduled-job fallback: when Railway runs a scheduled job with a
# custom command (e.g. `npm run producer:cc`), the entrypoint receives
# the command as its first argument. If SERVICE_ROLE is not one of the
# known values and a command is supplied, exec the command so the
# scheduled job runs whatever the operator asked for.
set -e

case "${SERVICE_ROLE:-server}" in
  worker)
    exec node src/worker.js
    ;;
  producer)
    exec node src/producer.js
    ;;
  producer-wc)
    exec node src/producer-woocommerce.js
    ;;
  producer-cc)
    exec node src/producer-cc-discover.js
    ;;
  producer-sitemap)
    exec node src/producer-sitemap.js
    ;;
  server)
    exec npm start
    ;;
  *)
    # Unknown SERVICE_ROLE but a command was passed (typical for
    # Railway scheduled jobs that override CMD). Forward the args so
    # `command: "npm run producer:cc"` actually runs the producer.
    if [ "$#" -gt 0 ]; then
      exec "$@"
    fi
    exec npm start
    ;;
esac
