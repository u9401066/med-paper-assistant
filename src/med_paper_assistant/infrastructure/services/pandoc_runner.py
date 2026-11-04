"""Pandoc subprocess helpers: argument validation and a time-limited runner."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - runs the pandoc binary with a timeout
import sys
from collections.abc import Callable

import pypandoc
import structlog

logger = structlog.get_logger()

DEFAULT_PANDOC_TIMEOUT_SECONDS = 180.0
_TIMEOUT_ENV_VAR = "MEDPAPER_PANDOC_TIMEOUT"


class PandocTimeoutError(RuntimeError):
    """Raised when the Pandoc subprocess exceeds its time limit."""


def pandoc_timeout_seconds() -> float:
    """Return the Pandoc time limit (``MEDPAPER_PANDOC_TIMEOUT`` overrides the default)."""
    raw = os.environ.get(_TIMEOUT_ENV_VAR, "").strip()
    try:
        value = float(raw) if raw else 0.0
    except ValueError:
        value = 0.0
    return value if value > 0 else DEFAULT_PANDOC_TIMEOUT_SECONDS


def reject_unc_path(value: str, field_name: str) -> None:
    """Refuse UNC/network paths, which would leak NTLM credentials on Windows."""
    if value.startswith(("\\\\", "//")):
        raise ValueError(f"{field_name} must not be a UNC/network path.")


def build_pandoc_args(
    *,
    reference_doc: str | None,
    csl: str | None,
    bibliography: str | None,
    extra_args: list[str] | None,
    filters: list[str] | None,
    resolve_csl: Callable[[str | None], str | None],
) -> list[str]:
    """Build the Pandoc CLI args, failing loudly when a requested asset is missing."""
    args = list(extra_args or [])
    if reference_doc:
        reject_unc_path(reference_doc, "reference_doc")
        if not os.path.isfile(reference_doc):
            raise FileNotFoundError(f"Reference document not found: {reference_doc}")
        args.extend(["--reference-doc", reference_doc])
    if csl:
        reject_unc_path(csl, "csl")
        csl_path = resolve_csl(csl)
        if not csl_path:
            raise FileNotFoundError(
                f"CSL style '{csl}' not found; refusing to export with Pandoc defaults"
            )
        args.extend(["--csl", csl_path])
    if bibliography:
        if not os.path.isfile(bibliography):
            raise FileNotFoundError(f"Bibliography file not found: {bibliography}")
        args.extend(["--bibliography", bibliography])
        if "--citeproc" not in args:
            args.append("--citeproc")
    for filter_name in filters or []:
        args.extend(["--filter", filter_name])
    if "--standalone" not in args and "-s" not in args:
        args.append("--standalone")
    return args


def run_pandoc(
    source: str,
    to: str,
    *,
    source_format: str,
    output_file: str | None,
    extra_args: list[str],
) -> str:
    """Run the Pandoc binary with a hard timeout and return its stdout text."""
    timeout = pandoc_timeout_seconds()
    command = [pypandoc.get_pandoc_path(), f"--from={source_format}", f"--to={to}"]
    if output_file:
        command.append(f"--output={output_file}")
    command.extend(extra_args)

    if to in {"pdf", "latex"}:
        setup_tinytex = getattr(pypandoc, "_try_setup_tinytex", None)
        if callable(setup_tinytex):
            setup_tinytex()
    env = os.environ.copy()
    files_dir = os.path.join(os.path.dirname(os.path.realpath(pypandoc.__file__)), "files")
    env["PATH"] = env.get("PATH", "") + os.pathsep + files_dir
    # Do not open a console window on Windows.
    creationflags = 0x08000000 if sys.platform == "win32" else 0

    try:
        completed = subprocess.run(  # nosec B603 - fixed pandoc binary, list args
            command,
            input=source.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            env=env,
            creationflags=creationflags,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PandocTimeoutError(
            f"Pandoc did not finish within {timeout:g}s and was terminated (converting to {to})."
        ) from exc

    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f'Pandoc died with exitcode "{completed.returncode}" during conversion: {stderr}'
        )
    if stderr.strip():
        logger.warning("pandoc_stderr", message=stderr.strip()[:500])
    return completed.stdout.decode("utf-8", errors="replace")


__all__ = [
    "DEFAULT_PANDOC_TIMEOUT_SECONDS",
    "PandocTimeoutError",
    "build_pandoc_args",
    "pandoc_timeout_seconds",
    "reject_unc_path",
    "run_pandoc",
]
