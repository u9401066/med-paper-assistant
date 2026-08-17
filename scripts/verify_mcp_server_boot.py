from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Literal

from med_paper_assistant.interfaces.mcp.server import create_server
from med_paper_assistant.interfaces.mcp.tool_surface import EXPECTED_TOOL_COUNTS

SurfaceSelection = Literal["compact", "full", "all"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the MCP server boots and registers expected assets."
    )
    parser.add_argument(
        "--surface",
        choices=("compact", "full", "all"),
        default="all",
        help="Tool surface to verify; 'all' checks both exact authority counts.",
    )
    parser.add_argument("--expected-prompts", type=int, default=3)
    parser.add_argument("--expected-resources", type=int, default=3)
    return parser.parse_args()


async def verify_server(surface: Literal["compact", "full"]) -> tuple[int, int, int]:
    """Boot the server and inspect assets through public MCP SDK 2 APIs."""
    mcp = create_server(surface)
    tools, prompts, resources = await asyncio.gather(
        mcp.list_tools(),
        mcp.list_prompts(),
        mcp.list_resources(),
    )
    return len(tools), len(prompts), len(resources)


def main() -> int:
    args = parse_args()
    selected: tuple[Literal["compact", "full"], ...] = (
        ("compact", "full") if args.surface == "all" else (args.surface,)
    )

    for surface in selected:
        tool_count, prompt_count, resource_count = asyncio.run(verify_server(surface))
        print(
            f"MCP {surface} server OK: {tool_count} tools, "
            f"{prompt_count} prompts, {resource_count} resources"
        )

        expected_tools = EXPECTED_TOOL_COUNTS[surface]
        if tool_count != expected_tools:
            print(
                f"Expected exactly {expected_tools} {surface} tools, got {tool_count}",
                file=sys.stderr,
            )
            return 1
        if prompt_count != args.expected_prompts:
            print(f"Expected {args.expected_prompts} prompts, got {prompt_count}", file=sys.stderr)
            return 1
        if resource_count != args.expected_resources:
            print(
                f"Expected {args.expected_resources} resources, got {resource_count}",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
