#!/usr/bin/env node

import { scrapeShopifyStore } from '../src/shopifyScraper.js';

console.log('Testing Shopify scraper for demo domain...');

const testDomain = 'store.anycubic.com';

scrapeShopifyStore(testDomain, 3)
  .then(products => {
    console.log(`\nScraped ${products.length} products from ${testDomain}:`);
    
    if (products.length > 0) {
      console.log('\nSample product:');
      console.log(JSON.stringify(products[0], null, 2));
      
      console.log('\nAll products:');
      products.forEach((p, i) => {
        console.log(`${i + 1}. ${p.title} - ${p.price} ${p.currency}`);
      });
    } else {
      console.log('No products found. This could be due to:');
      console.log('- Domain is not a valid Shopify store');
      console.log('- Network issues');
      console.log('- Sitemap changes');
    }
  })
  .catch(err => {
    console.error('Test failed:', err);
    process.exit(1);
  });