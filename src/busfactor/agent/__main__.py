"""Command-line entry point for agent questions and per-user memory inspection."""
import argparse
import json

from .llm import create_llm
from .loop import ask
from .memory import Memory


def main():
    parser = argparse.ArgumentParser(prog="python -m busfactor.agent")
    commands = parser.add_subparsers(dest="command", required=True)
    question = commands.add_parser("ask", help="ask the Delta graph")
    question.add_argument("question")
    question.add_argument("--user", required=True)
    question.add_argument("--session")
    memory = commands.add_parser("memory", help="inspect one user's memory graph")
    memory.add_argument("--user", required=True)
    args = parser.parse_args()
    if args.command == "memory":
        print(json.dumps(Memory(args.user).snapshot(), indent=2, ensure_ascii=False, default=str))
        return
    result = ask(args.question, args.user, args.session, create_llm())
    print(result["answer"])
    print("Tool trail:")
    for item in result["tool_calls"]:
        print(f"- {item['tool']} params={json.dumps(item['params'], sort_keys=True)} rows={item['row_count']} ms={item['ms']} tool_result_chars={item['tool_result_chars']}")
    print(f"Evidence graph: {len(result['graph']['nodes'])} nodes, {len(result['graph']['edges'])} edges")


if __name__ == "__main__":
    main()
