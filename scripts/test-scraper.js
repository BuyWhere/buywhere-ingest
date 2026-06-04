#!/usr/bin/env node

import dotenv from 'dotenv';
import { scrapeShopifyStore } from '../src/shopifyScraper.js';

dotenv.config();

const testDomain = process.env.SHOPIFY_DOMAIN || 'store.anycubic.com';

console.log(`Testing Shopify scraper for ${testDomain}...`);

try {
  const products = await scrapeShopifyStore(testDomain, 5);
  console.log(`\nScrape completed. Found ${products.length} products:`);
  
  if (products.length > 0) {
    console.log('\nSample product:');
    console.log(JSON.stringify(products[0], null, 2));
  }
} catch (err) {
  console.error('Scrape failed:', err);
  process.exit(1);
}