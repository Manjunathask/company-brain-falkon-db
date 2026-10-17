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
