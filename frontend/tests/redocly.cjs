const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {createRequire} = require('node:module');
const {adapt} = require('../scripts/adapt-redocly.cjs');
const requireInstalled = createRequire(process.cwd() + '/package.json');
const fromGenerator = createRequire(requireInstalled.resolve('openapi-typescript'));
const {readFileFromUrl} = fromGenerator('@redocly/openapi-core');
const source = readFileSync(fromGenerator.resolve('@redocly/openapi-core/lib/utils.js'), 'utf8');
assert.equal(adapt(adapt(source)), adapt(source));
assert.throws(() => adapt(source + '\n'), /Redocly changed/);

(async () => {
  for (const [url, expected] of [
    ['https://schemas.example.org/api/schema.json', {'X-Schema': 'fixture', 'X-Host': 'fixture'}],
    ['https://schemas.example.org/other/schema.json', {'X-Host': 'fixture'}],
    ['https://other.example.org/api/schema.json', {}],
  ]) {
    const result = await readFileFromUrl(url, {
      headers: [
        {name: 'X-Schema', value: 'fixture', matches: 'https://schemas.example.org/api/**'},
        {name: 'X-Host', value: 'fixture', matches: 'schemas.example.org/**'},
      ],
      customFetch: async (requested, options) => {
        assert.equal(requested, url);
        assert.deepEqual(options.headers, expected);
        return new Response('{"openapi":"3.1.0"}', {headers: {'content-type': 'application/json'}});
      },
    });
    assert.deepEqual(result, {body: '{"openapi":"3.1.0"}', mimeType: 'application/json'});
  }
  console.log('PASS Redocly: URL header matching and minimatch adapter guards');
})().catch(error => { console.error(error); process.exitCode = 1; });
