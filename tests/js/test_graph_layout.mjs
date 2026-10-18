import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sourceUrl = new URL("../../web/graph.js", import.meta.url);
const source = await readFile(sourceUrl, "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { evidenceLayout, widestRow } = await import(moduleUrl);

const graph = {
  nodes: [
    { id: 1, key: "decision:managed-commits", props: { slug: "managed-commits" } },
    { id: 2, key: "person:harperjiang", props: { login: "harperjiang" } },
  ],
  edges: [{ source: 1, target: 2 }],
};

const departure = evidenceLayout(graph, [], "departure");
assert.equal(departure.name, "concentric");
const element = className => ({ hasClass: value => value === className });
assert.equal(departure.concentric(element("departing")), 3);
assert.equal(departure.concentric(element("component")), 2);
assert.equal(departure.concentric(element("decision")), 2);
assert.equal(departure.concentric(element("person")), 1);
assert.equal(departure.levelWidth(), 1);

const unmatched = evidenceLayout(graph, ["Managed Commits"]);
assert.deepEqual(unmatched, { name: "breadthfirst", directed: false });
assert.equal(Object.hasOwn(unmatched, "roots"), false);
assert.equal(Object.hasOwn(evidenceLayout(graph, []), "roots"), false);
assert.deepEqual(evidenceLayout(graph, ["managed-commits"]).roots, ["1"]);
assert.deepEqual(evidenceLayout(graph, ["harperjiang"]).roots, ["2"]);
assert.deepEqual(evidenceLayout(graph, ["decision:managed-commits"]).roots, ["1"]);
const pathGraph = { ...graph, nodes: [{ id: 3, props: { path: "spark/A.scala" } }, graph.nodes[1]] };
assert.deepEqual(evidenceLayout(pathGraph, ["spark/A.scala"]).roots, ["3"]);
const departingGraph = { ...graph, nodes: [{ ...graph.nodes[0], focusRole: "departing" }, graph.nodes[1]] };
assert.deepEqual(evidenceLayout(departingGraph).roots, ["1"]);

assert.deepEqual(evidenceLayout({ nodes: [graph.nodes[0]], edges: [] }), { name: "cose", animate: false });
assert.deepEqual(evidenceLayout({ ...graph, edges: [] }), { name: "cose", animate: false });
assert.deepEqual(evidenceLayout({ nodes: [], edges: [] }), { name: "cose", animate: false });

const positioned = ys => ys.map(y => ({ position: dim => {
  assert.equal(dim, "y");
  return y;
} }));
assert.equal(widestRow(positioned([0, 0.2, 100, 100, 100])), 3);
assert.equal(widestRow(positioned([0.49, 0.51, 1.2])), 2);
assert.equal(widestRow([]), 0);
const nodes = positioned([10, 10.2, 50]);
assert.equal(widestRow({ 0: nodes[0], 1: nodes[1], 2: nodes[2], length: 3 }), 2);
console.log("graph layout preserves departure, omits unmatched roots, matches string ids, and counts rounded rows");
