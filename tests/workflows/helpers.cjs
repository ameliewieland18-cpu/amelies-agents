// Run an exported n8n Code node with fake inputs, without installing n8n.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');

// Example: result = runNode('wikijs-embeddings-index', 'Extract page list', [response]);
function runNode(workflow, name, values, earlier = {}) {
  const file = path.join(root, 'workflows', workflow + '.json');
  const document = JSON.parse(fs.readFileSync(file, 'utf8'));
  const code = document.nodes.find(node => node.name === name).parameters.jsCode;
  const items = structuredClone(values).map(json => ({json}));
  const result = vm.runInNewContext('(function(){\n' + code + '\n})()', {
    items,
    $json: items[0]?.json,
    $input: {all: () => items},
    $items: nodeName => structuredClone(earlier[nodeName] || []).map(json => ({json})),
  });
  // Convert values from the isolated VM into ordinary objects for comparisons.
  return JSON.parse(JSON.stringify(result));
}

module.exports = {runNode, root};
