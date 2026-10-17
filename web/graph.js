export const GRAPH_CAP = 60;

function nodeText(node) {
  const props = node.props || {};
  return props.login || props.path || props.number && `PR #${props.number}` || props.title || node.key || node.label || "Evidence";
}
function shortLabel(node) {
  const props = node.props || {};
  const value = props.login || props.path?.split("/").pop() || (props.number && `PR #${props.number}`) || props.title || node.key || node.label || "?";
  return String(value).length > 28 ? `${String(value).slice(0, 27)}…` : String(value);
}
function mainNode(node, roots) {
  const key = node.key || node.props?.login || node.props?.path || node.props?.slug;
  return roots.some(root => root && (root === key || root === node.props?.login || root === node.props?.path || root === node.props?.slug));
}

// BFS from explicit evidence roots; every returned edge has both endpoints in the retained set.
export function capConnectedGraph(graph = {}, roots = [], maxNodes = GRAPH_CAP) {
  const nodes = graph.nodes || [], edges = graph.edges || [];
  const byId = new Map(nodes.map(node => [node.id, node]));
  const adjacency = new Map(nodes.map(node => [node.id, []]));
  for (const edge of edges) {
    if (adjacency.has(edge.source) && adjacency.has(edge.target)) {
      adjacency.get(edge.source).push(edge.target);
      adjacency.get(edge.target).push(edge.source);
    }
  }
  const queue = nodes.filter(node => node.focusRole === "departing" || mainNode(node, roots)).map(node => node.id);
  if (!queue.length && nodes.length) queue.push(nodes[0].id);
  const kept = new Set();
  while (queue.length && kept.size < maxNodes) {
    const id = queue.shift();
    if (kept.has(id) || !byId.has(id)) continue;
    kept.add(id);
    for (const neighbor of adjacency.get(id) || []) if (!kept.has(neighbor)) queue.push(neighbor);
  }
  return {
    graph: { nodes: nodes.filter(node => kept.has(node.id)), edges: edges.filter(edge => kept.has(edge.source) && kept.has(edge.target)) },
    totalNodes: nodes.length,
    omitted: Math.max(0, nodes.length - kept.size),
  };
}

export function renderEvidence(panel, graph = {}, options = {}) {
  const canvas = panel.querySelector(".graph-canvas"), count = panel.querySelector(".graph-count");
  const detail = panel.querySelector(".node-properties"), list = panel.querySelector(".evidence-text ul");
  const allNodes = graph.nodes || [], allEdges = graph.edges || [];
  const cap = capConnectedGraph(graph, options.roots || [], GRAPH_CAP), shown = cap.graph;
  count.textContent = `${shown.nodes.length} nodes · ${shown.edges.length} links${cap.omitted ? ` · showing ${shown.nodes.length} of ${cap.totalNodes} nodes` : ""}`;
  list.replaceChildren();
  for (const node of shown.nodes) {
    const li = document.createElement("li"), text = nodeText(node);
    const link = githubUrl(node);
    if (link) { const a = document.createElement("a"); a.href = link; a.target = "_blank"; a.rel = "noopener"; a.textContent = text; li.append(a); }
    else li.textContent = text;
    const risk = node.risk || node.props?.risk;
    if (risk) { const badge = document.createElement("span"); badge.className = "risk-badge"; badge.textContent = risk; li.append(" ", badge); }
    list.append(li);
  }
  if (!shown.nodes.length) list.append(Object.assign(document.createElement("li"), { textContent: "Evidence paths will appear here after a graph answer." }));
  const old = canvas._cy;
  if (old) old.destroy();
  canvas.replaceChildren();
  if (!window.cytoscape || !shown.nodes.length) {
    count.textContent = shown.nodes.length ? `${shown.nodes.length} nodes · visual graph unavailable; see evidence as text` : "No graph evidence returned";
    return;
  }
  const elements = [
    ...shown.nodes.map(node => ({ data: { id: String(node.id), label: shortLabel(node), detail: nodeText(node), raw: node }, classes: `${String(node.label || "other").toLowerCase()}${node.risk ? ` ${node.risk.toLowerCase().replaceAll(" ", "-")}` : ""}`, ...(node.focusRole === "departing" ? { classes: "person departing" } : {}) })),
    ...shown.edges.map((edge, i) => ({ data: { id: `e${i}`, source: String(edge.source), target: String(edge.target), label: edge.type || "" } })),
  ];
  canvas._cy = window.cytoscape({ container: canvas, elements, style: [
    { selector: "node", style: { "label": "data(label)", "font-size": 10, "text-wrap": "wrap", "text-max-width": 92, "text-valign": "center", "text-halign": "center", "background-color": "#5276bd", color: "#17233b", "text-outline-width": 2, "text-outline-color": "#fff", width: 40, height: 40, "border-width": 1, "border-color": "#fff" } },
    { selector: "node.component", style: { "background-color": "#db932c", shape: "round-rectangle" } },
    { selector: "node.file", style: { "background-color": "#1c9d83", shape: "round-rectangle" } },
    { selector: "node.decision", style: { "background-color": "#bf5580", shape: "diamond" } },
    { selector: "node.commit, node.pullrequest, node.issue", style: { "background-color": "#9270bd", shape: "hexagon" } },
    { selector: "node.orphaned", style: { "border-width": 4, "border-color": "#a82e2e" } },
    { selector: "node.at-risk", style: { "border-width": 4, "border-color": "#ac6b06" } },
    { selector: "node.departing", style: { "width": 54, height: 54, "background-color": "#183c84", color: "#fff", "text-outline-color": "#183c84", "border-width": 3, "border-color": "#7b9fe9" } },
    { selector: "edge", style: { width: 1, "line-color": "#aab5c7", "target-arrow-color": "#aab5c7", "target-arrow-shape": "triangle", "curve-style": "bezier", "label": "data(label)", "font-size": 7, "text-rotation": "autorotate", "text-background-color": "#fff", "text-background-opacity": .8 } },
    { selector: ":selected", style: { "border-width": 4, "border-color": "#14264a" } },
  ], layout: options.layout === "departure" ? { name: "concentric", concentric: ele => ele.hasClass("departing") ? 3 : 1, levelWidth: () => 1 } : shown.nodes.length > 1 && shown.edges.length ? { name: "breadthfirst", directed: false, roots: shown.nodes.filter(node => node.focusRole === "departing" || mainNode(node, options.roots || [])).map(node => String(node.id)) } : { name: "cose", animate: false }, minZoom: .3, maxZoom: 2.5, userZoomingEnabled: true });
  canvas._cy.on("tap", "node", event => { detail.textContent = JSON.stringify(event.target.data("raw"), null, 2); });
  panel.querySelector(".fit-graph").onclick = () => canvas._cy?.fit(undefined, 24);
  panel.querySelector(".reset-graph").onclick = () => { canvas._cy?.layout(options.layout === "departure" ? { name: "concentric" } : { name: "breadthfirst" }).run(); canvas._cy?.fit(undefined, 24); };
  panel.querySelector(".zoom-in").onclick = () => canvas._cy?.zoom(canvas._cy.zoom() * 1.2);
  panel.querySelector(".zoom-out").onclick = () => canvas._cy?.zoom(canvas._cy.zoom() / 1.2);
}

function githubUrl(node) {
  const props = node.props || {}, label = String(node.label || "").toLowerCase();
  const number = props.number || node.key?.match(/(?:PR|#)(\d+)/i)?.[1];
  if (label.includes("pullrequest") || label === "pr") return number ? `https://github.com/delta-io/delta/pull/${number}` : null;
  if (label.includes("issue")) return number ? `https://github.com/delta-io/delta/issues/${number}` : props.url || null;
  if (label.includes("commit")) return `https://github.com/delta-io/delta/commit/${props.sha || node.key}`;
  if (label.includes("file") && (props.path || node.key)) return `https://github.com/delta-io/delta/blob/HEAD/${props.path || node.key}`;
  return null;
}
