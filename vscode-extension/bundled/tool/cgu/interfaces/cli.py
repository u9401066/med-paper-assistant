"""`cgu doctor`, `cgu serve` and `cgu inquiry`. Heavy modules are imported inside the commands,
so `cgu inquiry hook` never pays for the MCP SDK.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from cgu import __version__
from cgu.infrastructure.config import Settings


def serve_main() -> None:
    from cgu.interfaces.mcp.server import main as run

    run()


def _data_dir_status(settings: Settings) -> dict[str, Any]:
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.data_dir / ".cgu-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"path": str(settings.data_dir), "writable": True}
    except OSError as error:
        return {"path": str(settings.data_dir), "writable": False, "error": str(error)}


async def _probe(settings: Settings) -> dict[str, Any]:
    import httpx

    from cgu.application.ports import EmbeddingUnavailableError
    from cgu.infrastructure.embedding import make_embedding

    async with httpx.AsyncClient(timeout=3.0) as client:
        requested = settings.provider == "ollama" or settings.embedding != "ngram"
        ollama: dict[str, Any] = {"url": settings.ollama_url, "requested": requested}
        if requested:
            try:
                response = await client.get(f"{settings.ollama_url}/api/tags")
                response.raise_for_status()
                models = [m.get("name") for m in response.json().get("models", [])]
                ollama.update(reachable=True, models=models)
            except (httpx.HTTPError, ValueError) as error:
                ollama.update(reachable=False, error=str(error))
        else:
            ollama.update(reachable=None, reason="not requested; reasoning is handled by the agent")
        embedding = make_embedding(settings, client)
        try:
            info = await embedding.describe()
            backend: dict[str, Any] = {"backend": info.backend, "semantic": info.semantic}
        except EmbeddingUnavailableError as error:
            backend = {"backend": "unavailable", "semantic": False, "error": str(error)}
    return {"ollama": ollama, "embedding": {"mode": settings.embedding, **backend}}


def doctor(settings: Settings, as_json: bool = False) -> int:
    import asyncio

    report: dict[str, Any] = {
        "version": __version__,
        "provider": settings.provider,
        "network": settings.network,
        "data_dir": _data_dir_status(settings),
        **asyncio.run(_probe(settings)),
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        embedding = report["embedding"]
        ollama = report["ollama"]
        print(f"CGU {report['version']}")
        print(f"provider:         {report['provider']}")
        print(f"embedding mode:   {embedding['mode']}")
        print(
            f"embedding:        {embedding['backend']} (semantic={str(embedding['semantic']).lower()})"
        )
        reachable = (
            "not requested (agent handles reasoning)"
            if not ollama["requested"]
            else "reachable"
            if ollama["reachable"]
            else f"NOT reachable ({ollama['error']})"
        )
        print(f"ollama:           {ollama['url']} {reachable}")
        print(f"network (search): {'on' if report['network'] else 'off'}")
        status = "writable" if report["data_dir"]["writable"] else "NOT writable"
        print(f"data dir:         {report['data_dir']['path']} ({status})")
        if not embedding["semantic"]:
            print(
                "note: semantic=false, so novelty measurements are char n-gram overlap, not meaning."
            )
    return 0 if report["data_dir"]["writable"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "inquiry":
        from cgu.interfaces.inquiry_cli import main as inquiry_main

        return inquiry_main(args_list[1:])
    parser = argparse.ArgumentParser(prog="cgu", description="Creativity Generation Unit")
    sub = parser.add_subparsers(dest="command")
    doctor_parser = sub.add_parser("doctor", help="print provider, embedding, data dir and Ollama")
    doctor_parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub.add_parser("serve", help="run the MCP server on stdio")
    sub.add_parser(
        "inquiry",
        help="local, opt-in memory of your own questions (cgu inquiry --help)",
        add_help=False,
    )
    args = parser.parse_args(args_list)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        settings = Settings.from_env()
    except ValueError as error:
        print(f"cgu: {error}", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return doctor(settings, args.json)
    serve_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
