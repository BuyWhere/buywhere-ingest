# Semantic Search — June 2026 Deliverable

**Issue**: BUY-48232
**Created**: 2026-06-14 UTC
**Status**: in_progress (definition phase)

## Deliverable Statement

Semantic search is a **June 2026 product feature** with the following concrete commitments:

| Field | Value |
|-------|-------|
| **Feature name** | Semantic Search (embedding-based product discovery) |
| **Owners** | Rex (infra delivery) + Reed (validation) |
| **Target ship date** | 2026-06-30 UTC |
| **Storage/index path** | OpenAI `text-embedding-3-small` embeddings → Railway PostgreSQL `pgvector` extension |
| **Current blocker** | No implementation exists; `semantic_search.py` is a stub returning `[]` |
| **Validation method** | 35-query harness accepting ≥85% success rate |

## What Semantic Search Means

Semantic search for BuyWhere is **embedding-based product discovery** that matches natural-language queries to products by meaning rather than keyword matching.

**Technical definition:**
- Embedding model: OpenAI `text-embedding-3-small` (1536 dimensions, cost-effective)
- Vector storage: PostgreSQL with `pgvector` extension on Railway
- Similarity search: Cosine distance (`<=>` operator)
- Rank fusion: Hybrid of vector similarity and FTS `ts_rank`

**User experience improvement:**
- "laptop for college" finds student-appropriate laptops without exact keyword match
- "phone with good camera" surfaces high-camera-score smartphones
- "budget gaming mouse" returns affordable gaming peripherals

## Storage and Index Path

### PostgreSQL Schema

```sql
-- Enable pgvector extension (one-time, requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to products table
ALTER TABLE products 
ADD COLUMN embedding vector(1536);

-- Create HNSW index for fast approximate nearest-neighbor search
CREATE INDEX idx_products_embedding_hnsw 
ON products USING hnsw (embedding vector_cosine_ops)
WHERE is_active = true AND embedding IS NOT NULL;

-- Create partial index for active products
CREATE INDEX idx_products_active_embedding 
ON products (embedding) 
WHERE is_active = true;
```

### API Changes

1. **Ingestion path**: Generate embeddings during catalog ingest
   - OpenAI batch API (`/v1/embeddings`) for bulk product titles
   - Store in `products.embedding` column
   - Cost estimate: ~$0.00002 per product × 85M products = $1,700 one-time

2. **Query path**: Add semantic search option to `/v1/products/search`
   - Embed user query via OpenAI API
   - Query `ORDER BY embedding <=> query_embedding LIMIT N`
   - Merge with FTS results via rank fusion (weighted sum)

## Current Blocker

**No implementation exists.**

Evidence from 2026-06-14 heartbeat:
- `.opencode_tmp/buywhere/app/services/semantic_search.py` is a stub returning `[]`
- No `embedding` column exists in `products` table
- No `pgvector` extension enabled in maglev database
- No vector indexes present in catalog DB

## Implementation Issues

### Phase 1: Database Setup (Rex)
**Issue**: TBD (child of BUY-48232)
- Enable `pgvector` extension on Railway PostgreSQL (requires Ops/superuser)
- Add `embedding vector(1536)` column to `products`
- Create HNSW index for similarity search
- **ETA**: 2026-06-18
- **Blocker**: Railway superuser access (Ops coordination required)

### Phase 2: Embedding Generation Pipeline (Rex)
**Issue**: TBD (child of BUY-48232)
- Build OpenAI batch embedding job for 85M products
- Backfill existing catalog (title-only embedding)
- Add real-time embedding generation to new product ingest
- **ETA**: 2026-06-25
- **Blocker**: OpenAI API key with appropriate quota; $1,700 one-time cost approval

### Phase 3: Search API Integration (Rex)
**Issue**: TBD (child of BUY-48232)
- Implement semantic query path in `/v1/products/search`
- Add `mode=semantic|hybrid|fts` parameter
- Rank fusion algorithm (vector + FTS)
- **ETA**: 2026-06-28
- **Blocker**: Dependent on Phase 1 + 2 completion

### Phase 4: Validation Harness (Reed)
**Issue**: BUY-37423 (existing search harness)
- Extend 35-query harness to include semantic queries
- Acceptance criterion: ≥85% success rate on semantic query set
- Compare semantic vs FTS precision/recall
- **ETA**: 2026-06-30
- **Blocker**: Dependent on Phase 3 completion

## Validation Method

Reed's validation will use the **existing 35-query harness** (BUY-37423) extended with semantic-specific test cases:

### Semantic Query Set (examples)

| Query | Expected behavior | FTS baseline | Semantic target |
|-------|------------------|-------------|------------------|
| "laptop for college" | Student-budget laptops | Zero/low | ≥80% precision |
| "phone with good camera" | High camera-score phones | Zero/low | ≥80% precision |
| "budget gaming mouse" | Affordable gaming mice | Zero/low | ≥80% precision |
| "running shoes for marathons" | Marathon-specific footwear | Zero/low | ≥80% precision |
| "wireless noise-canceling headphones" | ANC headphones | Mixed | ≥90% precision |

### Acceptance Criteria

- **Overall success rate**: ≥85% across semantic query set
- **Improvement over FTS**: ≥50pp relative improvement for "natural language" queries
- **Latency**: p95 <200ms for semantic search (including embedding generation)
- **Cost**: < $0.001 per query (OpenAI embedding API cost)

## Next Actions

1. **Rex**: Create child issues for Phase 1-3 with concrete ETAs
2. **Rex**: Coordinate with Ops for `pgvector` extension enablement
3. **Reed**: Prepare semantic query set for harness extension
4. **Rich**: Approve $1,700 one-time embedding cost (Phase 2 blocker)

## Risk Factors

| Risk | Mitigation |
|------|------------|
| Railway doesn't support `pgvector` | Fallback to standalone vector service (Weaviate/Qdrant) |
| OpenAI API rate limits during backfill | Batch processing with exponential backoff |
| Embedding cost exceeds budget | Phase 1: embed top 10M products by query volume only |
| Semantic relevance fails acceptance | Fallback to hybrid FTS+semantic rank fusion |

## Source of Truth

- This document: `docs/semantic-search-june-deliverable-2026-06-14.md`
- Parent issue: BUY-48232
- Implementation issues: TBD (children to be created)
- Validation harness: BUY-37423
