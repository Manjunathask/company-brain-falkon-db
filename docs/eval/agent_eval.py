"""Reviewer eval: run demo questions through the live agent on one or more models and record the results.

Usage (env must carry ANTHROPIC_API_KEY and ANTHROPIC_WORKSPACE_ID):
  python agent_eval.py <out.json> <model> [<model> ...] [--only N]
"""
import json
import sys
import time
import uuid

sys.path.insert(0, r"C:\Users\skman\Documents\Hackathon\src")

from busfactor.agent.llm import AnthropicLLM  # noqa: E402
from busfactor.agent.loop import ask  # noqa: E402
from falkordb import FalkorDB  # noqa: E402

QUESTIONS = [
    "What does the project lose if scottsand-db leaves?",
    "If huan233usc left, who should take over their kernel-spark work?",
    "Why does the IcebergCompat metadata validator in Delta Kernel work the way it does? Trace it to a decision.",
    "Why was Managed Commits rejected, and what replaced it?",
    "Where do the declared CODEOWNERS differ from the people actually doing the work?",
]


def main():
    args = sys.argv[1:]
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = int(args[i + 1])
        del args[i:i + 2]
    out, models = args[0], args[1:]
    questions = QUESTIONS[:only] if only else QUESTIONS
    results = []
    for spec in models:
        model, _, effort = spec.partition(":")
        effort = effort or "medium"
        user = f"eval_{model.replace('-', '_')}_{effort}_{uuid.uuid4().hex[:6]}"
        llm = AnthropicLLM(model=model, effort=effort)
        for q in questions:
            t0 = time.perf_counter()
            try:
                a = ask(q, user, f"s-{uuid.uuid4().hex[:8]}", llm)
                a = a if isinstance(a, dict) else getattr(a, "__dict__", {"answer": str(a)})
                err = None
            except Exception as exc:  # report, keep going
                a, err = {}, f"{type(exc).__name__}: {exc}"
            secs = time.perf_counter() - t0
            results.append({"model": model, "effort": effort, "question": q, "seconds": round(secs, 1), "error": err,
                            "answer": a.get("answer"), "stop": a.get("stop_reason"),
                            "tools": [(c.get("tool"), c.get("params"), c.get("row_count")) for c in a.get("tool_calls", [])],
                            "usage": a.get("usage"),
                            "graph": {k: len(v) for k, v in (a.get("graph") or {}).items()}})
            r = results[-1]
            print(f"[{model}:{effort}] {secs:5.1f}s tools={len(r['tools'])} stop={r['stop']} err={err} :: {q[:60]}", flush=True)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=2, default=str, ensure_ascii=False)
        db = FalkorDB()
        if f"mem_{user}" in db.list_graphs():
            db.select_graph(f"mem_{user}").delete()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str, ensure_ascii=False)


if __name__ == "__main__":
    main()
