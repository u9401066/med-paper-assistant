from __future__ import annotations

import argparse
import sys

from med_paper_assistant.interfaces.mcp.server import create_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the MCP server boots and registers expected assets."
    )
    parser.add_argument("--min-tools", type=int, default=50)
    parser.add_argument("--expected-prompts", type=int, default=3)
    parser.add_argument("--expected-resources", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mcp = create_server()

    tool_count = len(mcp._tool_manager._tools)
    prompt_count = len(mcp._prompt_manager._prompts)
    resource_count = len(mcp._resource_manager._resources)

    print(f"MCP server OK: {tool_count} tools, {prompt_count} prompts, {resource_count} resources")

    if tool_count < args.min_tools:
        print(f"Expected at least {args.min_tools} tools, got {tool_count}", file=sys.stderr)
        return 1
    if prompt_count != args.expected_prompts:
        print(f"Expected {args.expected_prompts} prompts, got {prompt_count}", file=sys.stderr)
        return 1
    if resource_count != args.expected_resources:
        print(
            f"Expected {args.expected_resources} resources, got {resource_count}", file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
