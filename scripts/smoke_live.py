"""Opt-in end-to-end check for the configured live Claude agent."""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("SKIP: set ANTHROPIC_API_KEY to run the live Claude smoke check.")
        return

    from busfactor.agent.loop import ask

    started = time.perf_counter()
    result = ask("How many collaboration groups are in the graph?", "smoke-live")
    seconds = time.perf_counter() - started
    names = [call.get("tool", "") for call in result.get("tool_calls", [])]
    print(f"stop_reason: {result['stop_reason']}")
    print(f"tools: {', '.join(names) if names else '(none)'}")
    print(f"seconds: {seconds:.2f}")


if __name__ == "__main__":
    main()
