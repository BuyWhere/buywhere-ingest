FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY scripts ./scripts
# BUY-34835: bundle (Kai added data dir 2026-06-27) the v14 WAT pool snapshot (43,650 candidate domains,
# 5MB) as the default candidate list for the `discover.cc` worker. The
# producer can override this with CC_CANDIDATE_LIST_URL (e.g. a Tranco
# slice hosted in R2, or a re-pulled WAT pool) without rebuilding the
# image.
COPY data ./data
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["server"]
