export const GRAPH_CAP = 60;
// More nodes than this side by side cannot be read in the evidence panel.
const MAX_ROW = 10;

function nodeText(node) {
  const props = node.props || {};
  return props.login || props.path || (props.number && `PR #${props.number}`) ||
    props.title || node.key || node.label || "Evidence";
}

function shortLabel(node) {
  const props = node.props || {};
  const value = props.login || props.path?.split("/").pop() ||
    (props.number && `PR #${props.number}`) || props.title || node.key || node.label || "?";
  return String(value).length > 28 ? `${String(value).slice(0, 27)}…` : String(value);
}

function mainNode(node, roots) {
  const key = node.key || node.props?.login || node.props?.path || node.props?.slug;
  return roots.some(root => root && (
    root === key ||
    root === node.props?.login ||
    root === node.props?.path ||
    root === node.props?.slug
  ));
}

// Departure graphs ring around the leaving person; other graphs grow as a tree from the asked-about node.
export function evidenceLayout(shown, roots = [], mode = "chat") {
  if (mode === "departure") {
    return {
      name: "concentric",
      concentric: element => element.hasClass("departing") ? 3
        : element.hasClass("component") || element.hasClass("decision") ? 2 : 1,
      levelWidth: () => 1,
    };
  }
  if (shown.nodes.length > 1 && shown.edges.length) {
    const rootIds = shown.nodes
      .filter(node => node.focusRole === "departing" || mainNode(node, roots))
      .map(node => String(node.id));
    const layout = { name: "breadthfirst", directed: false };
    // An empty roots list puts every node on one row; omit it so Cytoscape picks roots.
    if (rootIds.length) layout.roots = rootIds;
    return layout;
  }
  return { name: "cose", animate: false };
}

// Breadthfirst puts each level of the tree on one row, so nodes in a row share a y position.
export function widestRow(nodes) {
  const rows = new Map();
  let widest = 0;
  for (const node of Array.from(nodes)) {
    const y = Math.round(node.position("y"));
    const count = (rows.get(y) || 0) + 1;
    rows.set(y, count);
    widest = Math.max(widest, count);
  }
  return widest;
}

// Retain a rooted breadth-first subgraph, reserving room for departure story nodes.
export function capConnectedGraph(graph = {}, roots = [], maxNodes = GRAPH_CAP) {
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  if (nodes.length <= maxNodes) {
    const ids = new Set(nodes.map(node => node.id));
    return {
      graph: { nodes, edges: edges.filter(edge => ids.has(edge.source) && ids.has(edge.target)) },
      totalNodes: nodes.length,
      omitted: 0,
    };
  }
  const byId = new Map(nodes.map(node => [node.id, node]));
  const adjacency = new Map(nodes.map(node => [node.id, []]));
  for (const edge of edges) {
    if (adjacency.has(edge.source) && adjacency.has(edge.target)) {
      adjacency.get(edge.source).push(edge.target);
      adjacency.get(edge.target).push(edge.source);
    }
  }

  // These nodes explain the departure and are kept even when that exceeds maxNodes.
  const priority = nodes.filter(node =>
    ["departing", "cut-off", "departure-decision"].includes(node.focusRole),
  );
  const kept = new Set(priority.map(node => node.id));
  const queue = [
    ...nodes.filter(node => node.focusRole === "departing"),
    ...priority.filter(node => node.focusRole !== "departing"),
    ...nodes.filter(node => mainNode(node, roots)),
  ].map(node => node.id);
  const expanded = new Set();
  if (!queue.length && nodes.length) queue.push(nodes[0].id);

  while (queue.length) {
    const id = queue.shift();
    if (expanded.has(id) || !byId.has(id)) continue;
    if (!kept.has(id) && kept.size >= maxNodes) continue;
    kept.add(id);
    expanded.add(id);
    for (const neighbor of adjacency.get(id) || []) {
      if (!kept.has(neighbor)) queue.push(neighbor);
    }
  }

  return {
    graph: {
      nodes: nodes.filter(node => kept.has(node.id)),
      edges: edges.filter(edge => kept.has(edge.source) && kept.has(edge.target)),
    },
    totalNodes: nodes.length,
    omitted: Math.max(0, nodes.length - kept.size),
  };
}

// Draw the capped graph and keep equivalent, readable evidence available as text.
export function renderEvidence(panel, graph = {}, options = {}) {
  panel.classList.toggle("is-placeholder", !(graph.nodes || []).length);
  const canvas = panel.querySelector(".graph-canvas");
  const count = panel.querySelector(".graph-count");
  const detail = panel.querySelector(".node-properties");
  const list = panel.querySelector(".evidence-text ul");
  const cap = capConnectedGraph(graph, options.roots || [], GRAPH_CAP);
  const shown = cap.graph;
  const omittedText = cap.omitted
    ? ` · showing ${shown.nodes.length} of ${cap.totalNodes} nodes`
    : "";
  count.textContent = `${shown.nodes.length} nodes · ${shown.edges.length} links${omittedText}`;
  list.replaceChildren();

  for (const node of shown.nodes) {
    const item = document.createElement("li");
    const text = nodeText(node);
    const link = githubUrl(node);
    if (link) {
      const anchor = document.createElement("a");
      anchor.href = link;
      anchor.target = "_blank";
      anchor.rel = "noopener";
      anchor.textContent = text;
      item.append(anchor);
    } else {
      item.textContent = text;
    }
    const risk = node.risk || node.props?.risk;
    if (risk) {
      const badge = document.createElement("span");
      badge.className = "risk-badge";
      badge.textContent = risk;
      item.append(" ", badge);
    }
    list.append(item);
  }
  if (!shown.nodes.length) {
    list.append(Object.assign(document.createElement("li"), {
      textContent: "Evidence paths will appear here after a graph answer.",
    }));
  }

  if (canvas._cy) canvas._cy.destroy();
  canvas.replaceChildren();
  if (!window.cytoscape || !shown.nodes.length) {
    count.textContent = shown.nodes.length
      ? `${shown.nodes.length} nodes · visual graph unavailable; see evidence as text`
      : "No graph evidence returned";
    return;
  }

  const elements = [
    ...shown.nodes.map(node => ({
      data: {
        id: String(node.id),
        label: shortLabel(node),
        detail: nodeText(node),
        raw: node,
      },
      classes: node.focusRole === "departing"
        ? "person departing"
        : `${String(node.label || "other").toLowerCase()}` +
          `${node.risk ? ` ${node.risk.toLowerCase().replaceAll(" ", "-")}` : ""}`,
    })),
    ...shown.edges.map((edge, index) => ({
      data: {
        id: `e${index}`,
        source: String(edge.source),
        target: String(edge.target),
        // Collapsed edges summarise several records ("reviewed 4 PRs here"); show that, not the type.
        label: edge.props?.summary || edge.type || "",
      },
      classes: [
        String(edge.type || "").toLowerCase(),
        edge.type === "IMPLEMENTS" && edge.props?.confidence === "low" ? "title-match" : "",
        edge.props?.collapsed ? "collapsed" : "",
      ].filter(Boolean).join(" "),
    })),
  ];

  const styles = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "font-size": 11,
        "text-wrap": "wrap",
        "text-max-width": 92,
        "text-valign": "center",
        "text-halign": "center",
        "background-color": "#5276bd",
        color: "#17233b",
        "text-outline-width": 2,
        "text-outline-color": "#fff",
        width: 40,
        height: 40,
        "border-width": 1,
        "border-color": "#fff",
      },
    },
    { selector: "node.component", style: { "background-color": "#db932c", shape: "round-rectangle" } },
    { selector: "node.file", style: { "background-color": "#1c9d83", shape: "round-rectangle" } },
    { selector: "node.decision", style: { "background-color": "#bf5580", shape: "diamond" } },
    {
      selector: "node.commit, node.pr, node.pullrequest, node.issue",
      style: { "background-color": "#9270bd", shape: "hexagon" },
    },
    { selector: "node.no-other-author", style: { "border-width": 4, "border-color": "#a82e2e" } },
    { selector: "node.one-other-author", style: { "border-width": 4, "border-color": "#ac6b06" } },
    {
      selector: "node.departing",
      style: {
        width: 54,
        height: 54,
        "background-color": "#183c84",
        color: "#fff",
        "text-outline-color": "#183c84",
        "border-width": 3,
        "border-color": "#7b9fe9",
      },
    },
    {
      selector: "edge",
      style: {
        width: 1,
        "line-color": "#aab5c7",
        "target-arrow-color": "#aab5c7",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": 7,
        "text-rotation": "autorotate",
        "text-background-color": "#fff",
        "text-background-opacity": 0.8,
      },
    },
    { selector: "edge.implements", style: { width: 2, "line-color": "#bf5580", "target-arrow-color": "#bf5580" } },
    { selector: "edge.title-match", style: { "line-style": "dashed" } },
    {
      selector: "edge.collapsed",
      style: { width: 2, "line-style": "dotted", "line-color": "#1c9d83", "target-arrow-color": "#1c9d83" },
    },
    { selector: ":selected", style: { "border-width": 4, "border-color": "#14264a" } },
  ];
  let layout = evidenceLayout(shown, options.roots || [], options.layout);

  canvas._cy = window.cytoscape({
    container: canvas,
    elements,
    style: styles,
    layout,
    minZoom: 0.3,
    maxZoom: 2.5,
    userZoomingEnabled: true,
  });
  // Breadthfirst draws each level as one row. More than MAX_ROW nodes in a row
  // cannot be read in the panel (a decision with 38 participants), so draw levels as rings.
  if (layout.name === "breadthfirst" && widestRow(canvas._cy.nodes()) > MAX_ROW) {
    layout = { ...layout, circle: true };
    canvas._cy.layout(layout).run();
  }
  canvas._cy.on("tap", "node", event => {
    detail.textContent = JSON.stringify(event.target.data("raw"), null, 2);
  });
  panel.querySelector(".fit-graph").onclick = () => canvas._cy?.fit(undefined, 24);
  panel.querySelector(".reset-graph").onclick = () => {
    canvas._cy?.layout(layout).run();
    canvas._cy?.fit(undefined, 24);
  };
  panel.querySelector(".zoom-in").onclick = () => canvas._cy?.zoom(canvas._cy.zoom() * 1.2);
  panel.querySelector(".zoom-out").onclick = () => canvas._cy?.zoom(canvas._cy.zoom() / 1.2);
}

function githubUrl(node) {
  const props = node.props || {};
  const label = String(node.label || "").toLowerCase();
  const number = props.number || node.key?.match(/(?:PR|#)(\d+)/i)?.[1];
  if (label.includes("pullrequest") || label === "pr") {
    return number ? `https://github.com/delta-io/delta/pull/${number}` : null;
  }
  if (label.includes("issue")) {
    return number ? `https://github.com/delta-io/delta/issues/${number}` : props.url || null;
  }
  if (label.includes("commit")) {
    return `https://github.com/delta-io/delta/commit/${props.sha || node.key}`;
  }
  if (label.includes("file") && (props.path || node.key)) {
    return `https://github.com/delta-io/delta/blob/HEAD/${props.path || node.key}`;
  }
  return null;
}
