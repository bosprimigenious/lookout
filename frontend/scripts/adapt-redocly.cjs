// Redocly 1.x calls minimatch 5's default export; v11 uses a named export.
const {createHash} = require('node:crypto');
const {readFileSync, writeFileSync} = require('node:fs');
const {createRequire} = require('node:module');
const original = '896a9acce92e3e5905aa267e895985d57888a87f500d58c29da9c8f9d488ff1c';
const anchor = 'const minimatch = require("minimatch");';
const replacement = 'const { minimatch } = require("minimatch");';

function adapt(source) {
  const pristine = source.includes(replacement) ? source.replace(replacement, anchor) : source;
  if (createHash('sha256').update(pristine).digest('hex') !== original || !pristine.includes(anchor)) {
    throw new Error('Redocly changed; review the minimatch adapter against tests/redocly.cjs');
  }
  return pristine.replace(anchor, replacement);
}

function main() {
  let generator;
  try {
    generator = require.resolve('openapi-typescript');
  } catch (error) {
    if (error.code === 'MODULE_NOT_FOUND' && error.message.startsWith("Cannot find module 'openapi-typescript'")) return;
    throw error;
  }
  const fromGenerator = createRequire(generator);
  const path = fromGenerator.resolve('@redocly/openapi-core/lib/utils.js');
  const source = readFileSync(path, 'utf8');
  const adapted = adapt(source);
  if (adapted !== source) writeFileSync(path, adapted);
}

if (require.main === module) main();
module.exports = {adapt};
