"""
MCP Tool Logging Utilities

提供統一的工具日誌記錄，包括：
- 工具呼叫參數記錄
- 執行結果記錄
- 錯誤追蹤（幫助分析 Agent 使用錯誤）
- 效能監控

裝飾器使用方式（注意順序！）:

    @with_tool_logging("save_reference")  # 先包裝 logging
    @mcp.tool()                           # 再註冊為 MCP tool
    def save_reference(article: dict) -> str:
        ...

或者手動呼叫:

    @mcp.tool()
    def save_reference(article: dict) -> str:
        log_tool_call("save_reference", {"article": article})
        try:
            result = do_something()
            log_tool_result("save_reference", result)
            return result
        except Exception as e:
            log_tool_error("save_reference", e, {"article": article})
            raise
"""

import functools
import json
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from med_paper_assistant.infrastructure.logging import get_logger

# Module-level logger for MCP tools
_tool_logger = None

# Module-level ToolInvocationStore singleton (None until initialize_tool_tracking is called)
_tool_store: Optional[Any] = None


def get_tool_logger():
    """Get the shared logger for MCP tools."""
    global _tool_logger
    if _tool_logger is None:
        _tool_logger = get_logger()
    return _tool_logger


def initialize_tool_tracking(workspace_root: Path) -> None:
    """
    Initialize workspace-level MCP tool invocation tracking.

    Must be called once from create_server() before tools are registered.
    After initialization, log_tool_call/result/error/misuse will also persist
    structured telemetry to workspace_root/.audit/tool-telemetry.yaml.

    Non-fatal: if initialization fails, telemetry is silently skipped and
    all tool executions continue normally.

    Args:
        workspace_root: Workspace root directory (parent of projects/).
    """
    global _tool_store
    try:
        from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
            ToolInvocationStore,
        )

        _tool_store = ToolInvocationStore(workspace_root)
        get_tool_logger().info(
            "tool_tracking_initialized",
            path=str(workspace_root / ".audit" / ToolInvocationStore.DATA_FILE),
        )
    except Exception as e:
        get_tool_logger().warning("tool_tracking_init_failed", error=str(e))


def _safe_serialize(obj: Any, max_length: int = 500) -> str:
    """Safely serialize an object for logging, truncating if too long."""
    try:
        if isinstance(obj, str):
            result = obj
        elif isinstance(obj, dict):
            result = json.dumps(obj, ensure_ascii=False, default=str)
        elif isinstance(obj, (list, tuple)):
            result = json.dumps(list(obj), ensure_ascii=False, default=str)
        else:
            result = str(obj)

        if len(result) > max_length:
            return result[:max_length] + f"... [truncated, total {len(result)} chars]"
        return result
    except Exception:
        return f"<unserializable: {type(obj).__name__}>"


def log_tool_call(tool_name: str, params: Dict[str, Any], caller_hint: str = "") -> None:
    """
    記錄工具被呼叫。

    Args:
        tool_name: 工具名稱
        params: 呼叫參數
        caller_hint: 呼叫者提示（如 Agent 類型）
    """
    logger = get_tool_logger()

    # 過濾敏感或過長的參數
    safe_params = {}
    for key, value in params.items():
        if key in ("password", "token", "api_key"):
            safe_params[key] = "***REDACTED***"
        else:
            safe_params[key] = _safe_serialize(value)

    caller_info = f" | caller={caller_hint}" if caller_hint else ""
    logger.debug(f"🔧 TOOL_CALL: {tool_name}{caller_info} | params={safe_params}")

    if _tool_store is not None:
        try:
            _tool_store.record_invocation(tool_name)
        except Exception:  # nosec B110 — telemetry must not crash tools
            pass


def log_tool_result(tool_name: str, result: Any, success: bool = True) -> None:
    """
    記錄工具執行結果。

    Args:
        tool_name: 工具名稱
        result: 執行結果
        success: 是否成功
    """
    logger = get_tool_logger()

    result_preview = _safe_serialize(result, max_length=300)
    status = "✅" if success else "⚠️"

    logger.debug(f"{status} TOOL_RESULT: {tool_name} | success={success} | result={result_preview}")

    if _tool_store is not None:
        try:
            if success:
                _tool_store.record_success(tool_name)
            else:
                _tool_store.record_error(tool_name)
        except Exception:  # nosec B110 — telemetry must not crash tools
            pass


def log_tool_error(
    tool_name: str,
    error: Exception,
    params: Optional[Dict[str, Any]] = None,
    context: Optional[str] = None,
) -> None:
    """
    記錄工具錯誤（包括 Agent 使用錯誤）。

    這些日誌對於分析 Agent 為何用錯工具非常重要！

    Args:
        tool_name: 工具名稱
        error: 錯誤例外
        params: 呼叫參數（用於重現問題）
        context: 額外的錯誤上下文
    """
    logger = get_tool_logger()

    safe_params = {}
    if params:
        for key, value in params.items():
            safe_params[key] = _safe_serialize(value)

    context_info = f" | context={context}" if context else ""

    # 記錄完整的 traceback 到 DEBUG 級別
    tb = traceback.format_exc()

    logger.error(f"❌ TOOL_ERROR: {tool_name} | {type(error).__name__}: {error}{context_info}")
    logger.debug(f"❌ TOOL_ERROR_DETAIL: {tool_name} | params={safe_params} | traceback:\n{tb}")

    if _tool_store is not None:
        try:
            _tool_store.record_error(tool_name, type(error).__name__)
        except Exception:  # nosec B110 — telemetry must not crash tools
            pass


def log_agent_misuse(
    tool_name: str, expected_usage: str, actual_params: Dict[str, Any], hint: str = ""
) -> None:
    """
    記錄 Agent 錯誤使用工具的情況。

    這對於分析和改進 Agent 行為非常重要！

    Args:
        tool_name: 工具名稱
        expected_usage: 預期的使用方式
        actual_params: 實際收到的參數
        hint: 給 Agent 的提示
    """
    logger = get_tool_logger()

    safe_params = {k: _safe_serialize(v) for k, v in actual_params.items()}

    logger.warning(
        f"🤖 AGENT_MISUSE: {tool_name} | "
        f"expected={expected_usage} | "
        f"actual_params={safe_params} | "
        f"hint={hint[:200] if hint else 'N/A'}"
    )

    if _tool_store is not None:
        try:
            _tool_store.record_misuse(tool_name)
        except Exception:  # nosec B110 — telemetry must not crash tools
            pass


def with_tool_logging(tool_name: str):
    """
    裝飾器：自動為工具函數加入日誌記錄。

    ⚠️ 注意裝飾器順序！必須放在 @mcp.tool() 之前：

        @with_tool_logging("save_reference")  # 先！
        @mcp.tool()                           # 後！
        def save_reference(article: dict) -> str:
            ...

    這樣 logging 會包裹整個 MCP tool 的執行。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 記錄呼叫
            log_tool_call(tool_name, kwargs if kwargs else {"args": args})

            try:
                result = func(*args, **kwargs)

                # 判斷是否成功（檢查結果是否包含錯誤標記）
                is_error = False
                if isinstance(result, str):
                    is_error = result.startswith("❌") or "Error" in result[:50]

                log_tool_result(tool_name, result, success=not is_error)

                # 如果是使用錯誤，額外記錄
                if is_error and isinstance(result, str):
                    log_agent_misuse(
                        tool_name,
                        expected_usage="See tool docstring",
                        actual_params=kwargs if kwargs else {"args": args},
                        hint=result,
                    )

                return result

            except Exception as e:
                log_tool_error(tool_name, e, kwargs if kwargs else {"args": args})
                raise

        return wrapper

    return decorator
