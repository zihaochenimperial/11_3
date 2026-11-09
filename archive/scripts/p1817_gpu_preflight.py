"""Fail-closed GPU availability preflight for P1817 GPU experiments.

Status: infrastructure smoke test only.  This module never initializes a GPU,
never loads a neural-network framework, and never kills another process.  It
runs ``nvidia-smi`` through subprocess argument lists and parses the resulting
text.

Scope:

* enumerate GPUs (index and UUID) with ``nvidia-smi --query-gpu=index,uuid``;
* enumerate active compute processes (PID and GPU UUID) with
  ``nvidia-smi --query-compute-apps=pid,gpu_uuid``;
* verify that a requested device index exists;
* reject the requested GPU if any compute process is attached to it;
* reject malformed output, missing tool, or nonzero exit (fail-closed);
* return structured availability information including an observation timestamp.

Important limitation
--------------------

This query is a point-in-time observation.  It cannot prevent another
non-cooperating job from starting on the requested GPU after the check
completes.  Callers must therefore also acquire a global exclusive lock
(e.g. a file lock, scheduler reservation, or mutex documented in the run
contract) before launching GPU work.
"""

from __future__ import annotations

import datetime
import re
import subprocess
from typing import Callable, Dict, List, Optional

__all__ = [
    "PreflightError",
    "parse_gpu_list",
    "parse_compute_apps",
    "gpu_preflight",
]


class PreflightError(RuntimeError):
    """Raised when the preflight check cannot prove the GPU is available."""


_NVIDIA_SMI = "nvidia-smi"
_GPU_UUID_RE = re.compile(r"^GPU-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_gpu_uuid(value: str, context: str) -> str:
    """Return a stripped GPU UUID or raise PreflightError."""
    uuid = value.strip()
    if not _GPU_UUID_RE.match(uuid):
        raise PreflightError(f"Malformed GPU UUID in {context}: {value!r}")
    return uuid


def parse_gpu_list(stdout: str) -> Dict[int, str]:
    """Parse ``nvidia-smi --query-gpu=index,uuid --format=csv,noheader`` output.

    Returns a mapping from integer GPU index to GPU UUID.  Raises
    :class:`PreflightError` for malformed or duplicate output.
    """
    gpus: Dict[int, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            raise PreflightError(f"Malformed GPU enumeration line: {raw_line!r}")
        index_str, uuid_str = parts
        try:
            index = int(index_str)
        except ValueError as exc:
            raise PreflightError(f"Non-integer GPU index: {index_str!r}") from exc
        if index < 0:
            raise PreflightError(f"Negative GPU index: {index}")
        uuid = _validate_gpu_uuid(uuid_str, f"GPU {index}")
        if index in gpus:
            raise PreflightError(f"Duplicate GPU index in enumeration: {index}")
        gpus[index] = uuid
    return gpus


def parse_compute_apps(stdout: str) -> List[Dict[str, object]]:
    """Parse ``nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv,noheader`` output.

    Returns a list of ``{"pid": int, "gpu_uuid": str}`` entries.  Lines that
    are blank or contain the known ``nvidia-smi`` "No running compute
    processes" message are ignored.  Malformed lines raise
    :class:`PreflightError`.
    """
    processes: List[Dict[str, object]] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # nvidia-smi sometimes emits a friendly message instead of CSV.
        if "No running compute processes" in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            raise PreflightError(f"Malformed compute-apps line: {raw_line!r}")
        pid_str, uuid_str = parts
        try:
            pid = int(pid_str)
        except ValueError as exc:
            raise PreflightError(f"Non-integer compute PID: {pid_str!r}") from exc
        if pid <= 0:
            raise PreflightError(f"Invalid compute PID: {pid}")
        uuid = _validate_gpu_uuid(uuid_str, f"PID {pid}")
        processes.append({"pid": pid, "gpu_uuid": uuid})
    return processes


def _run_query(args: List[str], _run: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    """Execute an ``nvidia-smi`` query and return stdout, fail-closed."""
    try:
        result = _run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise PreflightError(f"GPU query command not found: {args[0]!r}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise PreflightError(
            f"GPU query failed with exit {exc.returncode}: {stderr}"
        ) from exc
    return result.stdout


def gpu_preflight(
    device_index: int,
    *,
    nvidia_smi: str = _NVIDIA_SMI,
    _run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Dict[str, object]:
    """Check whether ``device_index`` is currently free of compute processes.

    The function enumerates GPUs, validates the requested index, queries
    running compute processes, and returns a structured result.  It never
    initializes the GPU.  Environmental failures (missing ``nvidia-smi``,
    nonzero exit, or unparseable output) raise :class:`PreflightError` to
    keep the check fail-closed.

    Args:
        device_index: integer CUDA-style device index to inspect.
        nvidia_smi: path or name of the ``nvidia-smi`` executable.
        _run: dependency-injection hook for subprocess execution; used by
            unit tests to mock ``nvidia-smi``.

    Returns:
        A dictionary with keys:

        * ``ok`` (bool): True iff the GPU exists and has no active compute
          processes.
        * ``device_index`` (int): the requested index.
        * ``gpu_uuid`` (str or None): UUID of the requested GPU, or None if
          the index does not exist.
        * ``timestamp`` (str): ISO 8601 UTC observation timestamp.
        * ``active_processes`` (list): compute processes on the requested GPU,
          each a ``{"pid": int, "gpu_uuid": str}`` dict.
        * ``message`` (str): human-readable summary.

    Raises:
        PreflightError: if the check cannot prove availability because of an
            infrastructure or parsing failure.
    """
    if not isinstance(device_index, int) or isinstance(device_index, bool):
        raise TypeError(f"device_index must be an integer, got {type(device_index).__name__}")

    timestamp = _utc_timestamp()

    gpu_stdout = _run_query(
        [nvidia_smi, "--query-gpu=index,uuid", "--format=csv,noheader"],
        _run,
    )
    gpus = parse_gpu_list(gpu_stdout)

    if device_index not in gpus:
        return {
            "ok": False,
            "device_index": device_index,
            "gpu_uuid": None,
            "timestamp": timestamp,
            "active_processes": [],
            "message": f"Device index {device_index} is not present (available indices: {sorted(gpus)}).",
        }

    target_uuid = gpus[device_index]

    apps_stdout = _run_query(
        [nvidia_smi, "--query-compute-apps=pid,gpu_uuid", "--format=csv,noheader"],
        _run,
    )
    processes = parse_compute_apps(apps_stdout)
    target_processes = [p for p in processes if p["gpu_uuid"] == target_uuid]

    if target_processes:
        message = (
            f"GPU {device_index} ({target_uuid}) has "
            f"{len(target_processes)} active compute process(es)."
        )
        return {
            "ok": False,
            "device_index": device_index,
            "gpu_uuid": target_uuid,
            "timestamp": timestamp,
            "active_processes": target_processes,
            "message": message,
        }

    message = f"GPU {device_index} ({target_uuid}) has no active compute processes."
    return {
        "ok": True,
        "device_index": device_index,
        "gpu_uuid": target_uuid,
        "timestamp": timestamp,
        "active_processes": [],
        "message": message,
    }
