// Indexing and report contracts, including generated export/source consistency.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const {runNode, root} = require('./helpers.cjs');

test('page listing keeps published pages and rejects missing data', () => {
  const pages = runNode('wikijs-embeddings-index', 'Extract page list', [{data: {pages: {list: [
    {id: 1, title: 'Services'}, {id: 2, isPublished: false}, null, {id: 3},
  ]}}}]);
  assert.deepEqual(pages.map(item => item.json.page_id), ['1', '3']);
  assert.throws(() => runNode('wikijs-embeddings-index', 'Extract page list', [{}]), /data.pages.list/);
});

test('index records contain stable hashes and complete chunk metadata', () => {
  const response = {data: {pages: {single: {
    id: 1, path: '/services', title: 'Services', content: 'x'.repeat(1300),
    updatedAt: '2026-09-21T12:00:00Z',
  }}}};
  const first = runNode('wikijs-embeddings-index', 'Prepare chunks', [response]);
  const second = runNode('wikijs-embeddings-index', 'Prepare chunks', [response]);
  assert.equal(first.length, 2);
  assert.equal(first[0].json.chunk_count, 2);
  assert.equal(first[1].json.chunk_index, 1);
  assert.equal(first[0].json.wiki_url, 'http://localhost:3000/services');
  assert.equal(first[0].json.content_hash, second[0].json.content_hash);
  assert.equal(first[1].json.metadata.chunk_index, 1);
  assert.throws(() => runNode('wikijs-embeddings-index', 'Prepare chunks', [{}]), /no page content/);
});

test('reports sort jobs, escape HTML, and keep output paths', () => {
  const [item] = runNode('job-search-nice-1', 'Build report document', [
    {role: 'Older', found_at: '2026-01-01'},
    {role: '<Designer>', company: 'A&B', found_at: '2026-09-21', full_description: 'one\ntwo'},
  ]);
  const report = item.json;
  assert.equal(report.job_count, 2);
  assert.match(report.report_markdown, /## 1\. <Designer> at A&B/);
  assert.match(report.report_html, /&lt;Designer&gt;/);
  assert.match(report.report_html, /A&amp;B/);
  assert.match(report.report_html, /one<br>two/);
  assert.equal(report.pdf_path, '/files/reports/job-search-report.pdf');
  const [empty] = runNode('job-search-nice-1', 'Build report document', []);
  assert.match(empty.json.report_markdown, /No jobs available/);
});

test('every code and SQL node is sourced and every exported script parses', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'workflow_sources/manifest.json')));
  for (const workflow of manifest) {
    const document = JSON.parse(fs.readFileSync(path.join(root, 'workflows', workflow.workflow)));
    for (const node of document.nodes) {
      for (const parameter of ['jsCode', 'query']) {
        if (!(parameter in node.parameters)) continue;
        assert.ok(workflow.nodes.some(entry => entry.name === node.name && entry.parameter === parameter));
        if (parameter === 'jsCode') assert.doesNotThrow(() => new Function(node.parameters[parameter]));
      }
    }
  }
});
