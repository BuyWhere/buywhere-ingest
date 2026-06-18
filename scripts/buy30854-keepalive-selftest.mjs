#!/usr/bin/env node
// Self-test process for the keep-alive's restart path
console.log(`[${new Date().toISOString()}] selftest pid=${process.pid} parent=${process.ppid} sid=${process.getsid?.() || process.pid}`);
setInterval(() => {
  // Stay alive
}, 30000);
