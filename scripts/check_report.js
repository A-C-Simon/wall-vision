// Exercise the generated report's selection and pointer handlers without network access.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const nodes = new Map();
function node() {
  return {
    children: [], value: 0, textContent: '',
    appendChild(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    setAttribute() {},
    getBoundingClientRect() { return {left: 0, width: 1000}; }
  };
}
const document = {
  getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); },
  createElement: node,
  createElementNS: node
};
const input = process.argv[2] || 'reports/public-benchmark.html';
const html = fs.readFileSync(input, 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInNewContext(script, {document}, {timeout: 5000});
assert.equal(nodes.get('session').children.length, 3);
assert.equal(nodes.get('still').textContent, 226);
nodes.get('session').value = 1;
nodes.get('session').onchange();
assert.equal(nodes.get('motion').textContent, 97);
nodes.get('plot').onpointermove({clientX: 500});
assert(nodes.get('cursor').textContent.includes('quality: ok'));
nodes.get('session').value = 2;
nodes.get('session').onchange();
assert.equal(nodes.get('still').textContent, 236);
console.log('Report session selection, score rendering, and pointer handler passed');
