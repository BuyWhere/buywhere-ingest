FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create an empty data/ directory at runtime. WAT pool snapshot and brand/retailer 
# lists are provided via CC_CANDIDATE_LIST_URL / SITEMAP_BRAND_LIST env vars at 
# runtime, not bundled in the image.
RUN mkdir -p /app/data && echo "# WAT pool + brand/retailer lists provided via env vars" > /app/data/README.md

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["server"]
