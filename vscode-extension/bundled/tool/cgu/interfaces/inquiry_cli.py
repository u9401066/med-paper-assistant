"""`cgu inquiry ...`: the local, opt-in memory of your own questions.

This module is imported lazily by `cgu.interfaces.cli`. Its top level, and the `hook` command, use
only the standard library plus a few stdlib-only CGU modules, so a hook that runs on every prompt
stays small: no MCP SDK, no pydantic, no numpy, no HTTP client.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cgu.infrastructure.config import Settings, copilot_home, data_dir_from_env

if TYPE_CHECKING:
    from cgu.application.services.inquiry import CaptureRequest, InquiryService
    from cgu.domain.common import ToolResult

HOOK_FILE = "cgu-inquiry.json"
HOOK_TIMEOUT_SEC = 15
MAX_STDIN_CHARS = 1_000_000
UVX_COMMAND = (
    "uvx --from git+https://github.com/u9401066/creativity-generation-unit@v0.9.0 cgu inquiry hook"
)
PRIVACY_NOTE = """提問記憶的隱私說明
- 預設關閉。啟用後，CGU 只在這台電腦記錄你送給 agent 的提問文字（去識別後最多 2000 字）、
  時間、來源管道與專案名稱（資料夾最後一段）。
- 不記錄助理回覆、工具輸出、檔案內容或完整路徑；不上傳、不同步、沒有遙測。
- 去識別只是盡力而為：email、電話、身分證字號、7 位以上數字與網址參數會被取代，
  但姓名與臨床細節不會被偵測。含病人資訊的提問請先改寫。
- hook 會在你每次送出提問時執行一個本機命令；它永遠不會阻擋你，錯誤只寫到 stderr。
- 隨時可用 cgu inquiry export 查看、cgu inquiry delete 刪除，或 --remove 移除 hook。"""


# --- hook ----------------------------------------------------------------------------------


def _record_from_hook(stdin: Any) -> None:
    import sqlite3

    from cgu.domain.capture import (
        FAMILY_JACCARD,
        capture_gate,
        clean_project,
        iso_from_epoch_ms,
        new_id,
        utc_now_iso,
    )
    from cgu.domain.lexical import best_lexical_match
    from cgu.domain.redaction import prepare_text
    from cgu.infrastructure import inquiry_sql
    from cgu.infrastructure.schema import MIGRATIONS, migrate

    raw = stdin.read(MAX_STDIN_CHARS)
    payload = json.loads(raw) if raw and raw.strip() else None
    if not isinstance(payload, dict):
        return
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return
    db_path = data_dir_from_env() / "cgu.sqlite3"
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path), timeout=2.0)
    try:
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("PRAGMA foreign_keys=ON")
        if int(conn.execute("PRAGMA user_version").fetchone()[0]) < len(MIGRATIONS):
            migrate(conn)
        enabled, excluded = inquiry_sql.load_gate(conn)
        cwd = payload.get("cwd")
        project = clean_project(cwd if isinstance(cwd, str) else None)
        if capture_gate(enabled, excluded, project) is not None:
            return
        stamp = payload.get("timestamp")
        try:
            occurred = iso_from_epoch_ms(float(stamp)) if isinstance(stamp, int | float) else None
        except (OverflowError, OSError, ValueError):
            occurred = None
        prepared = prepare_text(prompt)
        if not prepared.text:
            return
        index = inquiry_sql.family_index(conn)
        match = best_lexical_match(
            prepared.text, [(i, text) for i, _family, text in index], FAMILY_JACCARD
        )
        inquiry_id = new_id("inq")
        family = (
            next(f for i, f, _t in index if i == match[0])
            if match
            else "fam-" + inquiry_id.split("-", 1)[1]
        )
        client = payload.get("sessionId")
        with conn:
            inquiry_sql.insert_inquiry(
                conn,
                {
                    "id": inquiry_id,
                    "text": prepared.text,
                    "source": "hook",
                    "project": project,
                    "occurred_at": occurred or utc_now_iso(),
                    "captured_at": utc_now_iso(),
                    "redactions": prepared.redactions,
                    "truncated": prepared.truncated,
                    "family_id": family,
                    "meta": {"client_session": client[:100]}
                    if isinstance(client, str) and client
                    else {},
                },
            )
    finally:
        conn.close()


def hook(stdin: Any = None) -> int:
    """Record one prompt if (and only if) the user enabled it. Never blocks, never prints."""
    try:
        _record_from_hook(sys.stdin if stdin is None else stdin)
    except Exception as error:  # a hook must never stop the user's prompt from going through
        print(f"cgu inquiry hook: {type(error).__name__}: {error}", file=sys.stderr)
    return 0


# --- install-hook --------------------------------------------------------------------------


def hook_command() -> str:
    return "cgu inquiry hook" if shutil.which("cgu") else UVX_COMMAND


def hook_config(command: str) -> dict[str, Any]:
    return {
        "version": 1,
        "hooks": {
            "userPromptSubmitted": [
                {
                    "type": "command",
                    "bash": command,
                    "powershell": command,
                    "timeoutSec": HOOK_TIMEOUT_SEC,
                }
            ]
        },
    }


def hook_path() -> Path:
    return copilot_home() / "hooks" / HOOK_FILE


def install_hook(*, print_only: bool, remove: bool) -> int:
    target = hook_path()
    if remove:
        if target.exists():
            target.unlink()
            print(f"已移除：{target}")
        else:
            print(f"沒有安裝（找不到 {target}）。")
        return 0
    command = hook_command()
    text = json.dumps(hook_config(command), indent=2, ensure_ascii=False)
    print(PRIVACY_NOTE)
    print()
    print(f"將寫入：{target}")
    print(text)
    if print_only:
        print("\n（--print：沒有寫入任何檔案。）")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="utf-8")
    print(f"\n已寫入 {target}。重新開啟 Copilot CLI 後生效。")
    print("hook 只在你啟用記錄後才會寫入：cgu inquiry settings --enable --yes")
    return 0


# --- commands that use the service ---------------------------------------------------------


def _run_service(
    settings: Settings, work: Callable[[InquiryService], Awaitable[ToolResult]]
) -> ToolResult:
    import asyncio

    async def go() -> ToolResult:
        import httpx

        from cgu.application.services.inquiry import InquiryService
        from cgu.infrastructure.embedding import make_embedding
        from cgu.infrastructure.sqlite import SQLiteArchive

        async with httpx.AsyncClient(timeout=15.0) as client:
            archive = SQLiteArchive(settings.db_path)
            try:
                return await work(InquiryService(archive, make_embedding(settings, client)))
            finally:
                archive.close()

    return asyncio.run(go())


def _emit(result: ToolResult, render: Callable[[dict[str, Any]], list[str]], as_json: bool) -> int:
    if not result.ok:
        message = result.error.message if result.error else "failed"
        print(f"cgu inquiry: {message}", file=sys.stderr)
        if result.error and result.error.hint:
            print(f"  {result.error.hint}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        for line in render(result.data):
            print(line)
        for warning in result.provenance.warnings:
            print(f"! {warning}")
    return 0


def _render_settings(data: dict[str, Any]) -> list[str]:
    state = {None: "從未詢問（未啟用）", True: "已啟用", False: "已停用／已拒絕"}[data["enabled"]]
    lines = [f"提問記憶：{state}"]
    consent = data.get("consent")
    if consent:
        lines.append(f"同意紀錄：{consent['via']}，{consent['at']}，「{consent['note']}」")
    lines.append(f"排除的專案：{', '.join(data['excluded_projects']) or '（無）'}")
    counts = data["counts"]
    lines.append(
        f"提問 {counts['inquiries']} 筆，family {counts['families']}，"
        f"主題 {counts['themes']}，已呈現的來源 {counts['sources']}"
    )
    lines.append(f"管道占比：{data['sources_by_channel']}")
    return lines


def _render_themes(data: dict[str, Any]) -> list[str]:
    lines = [
        f"主題 {len(data['themes'])} 個；未歸類的提問 {data['uncategorized']} 筆；"
        f"管道占比 {data['channels']}"
    ]
    for theme in data["themes"]:
        name = theme["label"] or "（未命名）"
        lines.append(
            f"- {theme['theme_id']} {name}：{theme['families']} 種問法，{theme['size']} 筆，"
            f"{theme['distinct_days']} 天（{theme['first_seen'][:10]} ～ {theme['last_seen'][:10]}）"
        )
        lines.extend(f"    · {e['text'][:60]}" for e in theme["exemplars"][:3])
    return lines


def _render_mine(data: dict[str, Any]) -> list[str]:
    lines = [f"來源 {len(data['sources'])} 個（參照集 {data['reference_size']} 筆提問）"]
    for source in data["sources"]:
        lines.append(f"- [{source['kind']}] {source['title']}")
        lines.extend(f"    · {e['text'][:60]}" for e in source["evidence"][:3])
    return lines


def _render_json(data: dict[str, Any]) -> list[str]:
    return [json.dumps(data, ensure_ascii=False, indent=2)]


def _cmd_settings(settings: Settings, args: argparse.Namespace) -> int:
    from cgu.domain.inquiry import InquiryConsent

    if args.enable and args.disable:
        print("cgu inquiry: --enable 與 --disable 不能同時使用", file=sys.stderr)
        return 2
    consent = None
    if args.enable:
        if not args.yes:
            print(PRIVACY_NOTE)
            print(
                "\n啟用需要你的同意：確認後請加上 --yes（在 CLI，--yes 即為同意）。",
                file=sys.stderr,
            )
            return 2
        consent = InquiryConsent(
            granted=True, note="cgu inquiry settings --enable --yes", via="cli"
        )
    enable = True if args.enable else (False if args.disable else None)
    result = _run_service(
        settings,
        lambda s: s.settings(
            enable=enable, consent=consent, excluded_projects=args.exclude or None
        ),
    )
    return _emit(result, _render_settings, args.json)


def _read_import(path: Path, project: str | None) -> list[CaptureRequest]:
    from cgu.application.services.inquiry import CaptureRequest

    requests: list[CaptureRequest] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        text, occurred, item_project = line, None, project
        if line.startswith("{"):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                row = None
            if isinstance(row, dict):
                if not isinstance(row.get("text"), str):
                    continue
                text = row["text"]
                occurred = (
                    row.get("occurred_at") if isinstance(row.get("occurred_at"), str) else None
                )
                if isinstance(row.get("project"), str):
                    item_project = row["project"]
        if text.strip():
            requests.append(
                CaptureRequest(
                    text=text, project=item_project, source="import", occurred_at=occurred
                )
            )
    return requests


def _cmd_import(settings: Settings, args: argparse.Namespace) -> int:
    from cgu.domain.capture import MAX_BATCH

    path = Path(args.file)
    if not path.is_file():
        print(f"cgu inquiry: 找不到檔案 {path}", file=sys.stderr)
        return 2
    requests = _read_import(path, args.project)
    if not requests:
        print("cgu inquiry: 檔案裡沒有可匯入的提問", file=sys.stderr)
        return 2

    async def work(service: InquiryService) -> ToolResult:
        from cgu.domain.redaction import merge_counts

        recorded = 0
        redactions: dict[str, int] = {}
        last: ToolResult | None = None
        for start in range(0, len(requests), MAX_BATCH):
            last = await service.capture(requests[start : start + MAX_BATCH], batch=True)
            if not last.ok or not last.data.get("recorded"):
                return last
            recorded += int(last.data["count"])
            redactions = merge_counts(redactions, last.data["redactions"])
        assert last is not None
        last.data.update(count=recorded, redactions=redactions)
        return last

    result = _run_service(settings, work)

    def render(data: dict[str, Any]) -> list[str]:
        if not data.get("recorded"):
            return [f"沒有匯入：{data.get('reason')}。{data.get('hint', '')}"]
        return [
            f"已匯入 {data['count']} 筆；去識別：{data['redactions']}",
            data["redaction_note"],
        ]

    code = _emit(result, render, args.json)
    return code if code else (0 if result.data.get("recorded") else 1)


def _cmd_list_like(settings: Settings, args: argparse.Namespace) -> int:
    if args.sub == "themes":
        result = _run_service(
            settings,
            lambda s: s.themes(
                min_size=args.min_size,
                threshold=args.threshold,
                project=args.project,
                since_days=args.since_days,
            ),
        )
        return _emit(result, _render_themes, args.json)
    if args.sub == "mine":
        result = _run_service(
            settings,
            lambda s: s.mine(kinds=args.kinds or None, limit=args.limit, project=args.project),
        )
        return _emit(result, _render_mine, args.json)
    result = _run_service(settings, lambda s: s.export(args.project))
    if args.output:
        Path(args.output).write_text(
            json.dumps(result.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"已匯出 {result.data['count']} 筆到 {args.output}")
        return 0
    return _emit(result, _render_json, False)


def _cmd_delete(settings: Settings, args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "cgu inquiry: delete 會連同向量、主題成員與來源紀錄一併刪除；確認後請加上 --yes",
            file=sys.stderr,
        )
        return 2
    result = _run_service(
        settings,
        lambda s: s.delete(
            ids=args.ids,
            project=args.project,
            older_than_days=args.older_than_days,
            everything=args.all,
            confirm=True,
        ),
    )

    def render(data: dict[str, Any]) -> list[str]:
        return [
            f"已刪除 {data['deleted']} 筆（移除主題 {data['themes_removed']}、"
            f"來源 {data['sources_removed']}）；剩下 {data['remaining']} 筆"
        ]

    return _emit(result, render, args.json)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cgu inquiry", description="Local, opt-in memory of your own questions"
    )
    sub = parser.add_subparsers(dest="sub")

    def add_json(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true", help="print the full result as JSON")

    p = sub.add_parser("settings", help="show or change whether questions are recorded")
    p.add_argument("--enable", action="store_true", help="start recording (needs --yes)")
    p.add_argument("--yes", action="store_true", help="your consent to --enable")
    p.add_argument("--disable", action="store_true", help="stop recording")
    p.add_argument("--exclude", nargs="+", metavar="PROJECT", help="never record these projects")
    add_json(p)

    sub.add_parser("hook", help="record one prompt from stdin (used by the Copilot hook)")

    p = sub.add_parser("import", help="import questions from a text or JSON-lines file")
    p.add_argument("file")
    p.add_argument("--project", help="project name for lines that have none")
    add_json(p)

    p = sub.add_parser("themes", help="cluster your questions into themes")
    p.add_argument("--min-size", type=int)
    p.add_argument("--threshold", type=float)
    p.add_argument("--project")
    p.add_argument("--since-days", type=int)
    add_json(p)

    p = sub.add_parser("mine", help="creative sources from your question history")
    p.add_argument("--kinds", nargs="+", choices=["frame", "bridge", "stalled", "dormant"])
    p.add_argument("--limit", type=int)
    p.add_argument("--project")
    add_json(p)

    p = sub.add_parser("export", help="export every stored question as JSON")
    p.add_argument("--project")
    p.add_argument("--output", help="write to this file instead of stdout")

    p = sub.add_parser("delete", help="delete questions (and their vectors, themes, sources)")
    p.add_argument("--ids", nargs="+")
    p.add_argument("--project")
    p.add_argument("--older-than-days", type=int)
    p.add_argument("--all", action="store_true")
    p.add_argument("--yes", action="store_true", help="confirm the deletion")
    add_json(p)

    p = sub.add_parser("install-hook", help="install the Copilot userPromptSubmitted hook")
    p.add_argument("--print", dest="print_only", action="store_true", help="show, do not write")
    p.add_argument("--remove", action="store_true", help="remove the hook file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "hook":
        return hook()
    parser = _parser()
    args = parser.parse_args(args_list)
    if args.sub is None:
        parser.print_help()
        return 2
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    if args.sub == "install-hook":
        return install_hook(print_only=args.print_only, remove=args.remove)
    try:
        settings = Settings.from_env()
    except ValueError as error:
        print(f"cgu: {error}", file=sys.stderr)
        return 2
    if args.sub == "settings":
        return _cmd_settings(settings, args)
    if args.sub == "import":
        return _cmd_import(settings, args)
    if args.sub == "delete":
        return _cmd_delete(settings, args)
    return _cmd_list_like(settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
