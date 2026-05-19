#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const expected = `${pkg.name}-${pkg.version}.vsix`;
const candidates = fs
  .readdirSync(root)
  .filter((name) => name.endsWith('.vsix'))
  .sort();

if (!candidates.length) {
  console.error('No VSIX package found. Run `npm run package` before install smoke.');
  process.exit(1);
}

if (!candidates.includes(expected)) {
  console.error(`Missing expected VSIX ${expected}. Found: ${candidates.join(', ')}`);
  process.exit(1);
}

const vsixPath = path.join(root, expected);
const size = fs.statSync(vsixPath).size;
if (size <= 0) {
  console.error(`VSIX ${expected} is empty.`);
  process.exit(1);
}

console.log(`VSIX smoke passed: ${expected} (${size} bytes)`);
