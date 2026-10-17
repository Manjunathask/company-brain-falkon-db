import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const sourceUrl = new URL("../../web/graph.js", import.meta.url);
const source = await readFile(sourceUrl, "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { capConnectedGraph } = await import(moduleUrl);

const graph = {
  nodes: [
    { id: 1, key: "alice", label: "Person", props: { login: "alice" }, focusRole: "departing" },
    { id: 2, key: "spark", label: "Component" },
    { id: 3, key: "file.scala", label: "File" },
    { id: 4, key: "disconnected", label: "Person" },
  ],
  edges: [
    { source: 1, target: 2, type: "KNOWS" },
    { source: 2, target: 3, type: "TOUCHED" },
    { source: 3, target: 4, type: "UNRELATED" },
  ],
};
const capped = capConnectedGraph(graph, [], 3);
assert.deepEqual(capped.graph.nodes.map(node => node.id), [1, 2, 3]);
assert.deepEqual(capped.graph.edges.map(edge => [edge.source, edge.target]), [[1, 2], [2, 3]]);
assert.equal(capped.omitted, 1);
console.log("graph cap keeps a rooted connected subgraph and only internal edges");

const storyGraph = {
  nodes: [
    { id: "gone", label: "Person", focusRole: "departing" },
    { id: "cutoff", label: "Person", focusRole: "cut-off" },
    { id: "decision", label: "Decision", focusRole: "departure-decision" },
    ...Array.from({ length: 8 }, (_, id) => ({ id: `filler-${id}`, label: "File" })),
  ],
  edges: [
    { source: "gone", target: "cutoff", type: "WORKS_WITH" },
    { source: "gone", target: "decision", type: "PARTICIPATED_IN" },
  ],
};
const story = capConnectedGraph(storyGraph, [], 2);
assert.deepEqual(new Set(story.graph.nodes.map(node => node.id)), new Set(["gone", "cutoff", "decision"]));
assert.equal(story.omitted, 8);
console.log("graph cap preserves cut-off people and departure decisions beyond the cap");
