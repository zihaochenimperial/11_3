"""Synthetic unit tests for scripts/p1817_gpu_preflight.py.

These tests exercise parsing and the orchestration function with mocked
``nvidia-smi`` output.  They do not run the real GPU tool, do not initialize
any GPU, and do not use clean truth or held-out data.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest
from typing import List, Optional

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
MODULE_PATH = SCRIPTS_DIR / "p1817_gpu_preflight.py"
sys.path.insert(0, str(SCRIPTS_DIR))

import p1817_gpu_preflight as gp  # noqa: E402

GPU_0_UUID = "GPU-00000000-1111-2222-3333-444444444444"
GPU_1_UUID = "GPU-55555555-6666-7777-8888-999999999999"


def _completed(stdout: str = "", stderr: Optional[str] = None, returncode: int = 0, args: Optional[List[str]] = None):
    return subprocess.CompletedProcess(
        args=args or [],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr or "",
    )


def make_mock_run(gpu_stdout: str, apps_stdout: str = ""):
    """Return a fake ``_run`` that returns canned nvidia-smi output."""
    def _run(args: List[str], **kwargs):
        if "--query-gpu=index,uuid" in args:
            return _completed(stdout=gpu_stdout, args=args)
        if "--query-compute-apps=pid,gpu_uuid" in args:
            return _completed(stdout=apps_stdout, args=args)
        raise AssertionError(f"Unexpected mocked command: {args}")
    return _run


class ParseGpuListTest(unittest.TestCase):
    def test_valid_enumeration(self):
        stdout = f"0, {GPU_0_UUID}\n1, {GPU_1_UUID}\n"
        gpus = gp.parse_gpu_list(stdout)
        self.assertEqual(gpus, {0: GPU_0_UUID, 1: GPU_1_UUID})

    def test_skips_blank_lines(self):
        stdout = f"\n0, {GPU_0_UUID}\n\n1, {GPU_1_UUID}\n\n"
        gpus = gp.parse_gpu_list(stdout)
        self.assertEqual(gpus, {0: GPU_0_UUID, 1: GPU_1_UUID})

    def test_malformed_line_wrong_columns(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_gpu_list(f"0, {GPU_0_UUID}\n2, extra, column\n")
        self.assertIn("Malformed GPU enumeration line", str(ctx.exception))

    def test_duplicate_index(self):
        stdout = f"0, {GPU_0_UUID}\n0, {GPU_1_UUID}\n"
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_gpu_list(stdout)
        self.assertIn("Duplicate GPU index", str(ctx.exception))

    def test_invalid_uuid(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_gpu_list("0, not-a-uuid\n")
        self.assertIn("Malformed GPU UUID", str(ctx.exception))

    def test_negative_index(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_gpu_list(f"-1, {GPU_0_UUID}\n")
        self.assertIn("Negative GPU index", str(ctx.exception))


class ParseComputeAppsTest(unittest.TestCase):
    def test_empty_output(self):
        self.assertEqual(gp.parse_compute_apps(""), [])
        self.assertEqual(gp.parse_compute_apps("   \n\n  "), [])

    def test_no_running_message(self):
        stdout = "No running compute processes found\n"
        self.assertEqual(gp.parse_compute_apps(stdout), [])

    def test_valid_processes(self):
        stdout = f"1234, {GPU_0_UUID}\n5678, {GPU_1_UUID}\n"
        procs = gp.parse_compute_apps(stdout)
        self.assertEqual(procs, [
            {"pid": 1234, "gpu_uuid": GPU_0_UUID},
            {"pid": 5678, "gpu_uuid": GPU_1_UUID},
        ])

    def test_malformed_line_wrong_columns(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_compute_apps("1234\n")
        self.assertIn("Malformed compute-apps line", str(ctx.exception))

    def test_invalid_pid(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_compute_apps(f"not-a-pid, {GPU_0_UUID}\n")
        self.assertIn("Non-integer compute PID", str(ctx.exception))

    def test_non_positive_pid(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_compute_apps(f"0, {GPU_0_UUID}\n")
        self.assertIn("Invalid compute PID", str(ctx.exception))

    def test_invalid_uuid(self):
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.parse_compute_apps("1234, bad-uuid\n")
        self.assertIn("Malformed GPU UUID", str(ctx.exception))


class GpuPreflightTest(unittest.TestCase):
    def test_empty_gpu_available(self):
        mock_run = make_mock_run(gpu_stdout=f"0, {GPU_0_UUID}\n")
        result = gp.gpu_preflight(0, _run=mock_run)
        self.assertTrue(result["ok"])
        self.assertEqual(result["device_index"], 0)
        self.assertEqual(result["gpu_uuid"], GPU_0_UUID)
        self.assertEqual(result["active_processes"], [])
        self.assertIn("no active compute processes", result["message"])
        self.assertIsInstance(result["timestamp"], str)
        self.assertTrue(result["timestamp"].endswith("Z"))

    def test_active_target_rejected(self):
        mock_run = make_mock_run(
            gpu_stdout=f"0, {GPU_0_UUID}\n1, {GPU_1_UUID}\n",
            apps_stdout=f"1234, {GPU_0_UUID}\n",
        )
        result = gp.gpu_preflight(0, _run=mock_run)
        self.assertFalse(result["ok"])
        self.assertEqual(result["gpu_uuid"], GPU_0_UUID)
        self.assertEqual(result["active_processes"], [{"pid": 1234, "gpu_uuid": GPU_0_UUID}])
        self.assertIn("active compute process", result["message"])

    def test_active_other_gpu_accepted(self):
        mock_run = make_mock_run(
            gpu_stdout=f"0, {GPU_0_UUID}\n1, {GPU_1_UUID}\n",
            apps_stdout=f"9999, {GPU_1_UUID}\n",
        )
        result = gp.gpu_preflight(0, _run=mock_run)
        self.assertTrue(result["ok"])
        self.assertEqual(result["active_processes"], [])

    def test_invalid_index(self):
        mock_run = make_mock_run(gpu_stdout=f"0, {GPU_0_UUID}\n")
        result = gp.gpu_preflight(5, _run=mock_run)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["gpu_uuid"])
        self.assertIn("not present", result["message"])

    def test_unavailable_command(self):
        def _run(args, **kwargs):
            raise FileNotFoundError("nvidia-smi")
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.gpu_preflight(0, _run=_run)
        self.assertIn("not found", str(ctx.exception))

    def test_nonzero_exit(self):
        def _run(args, **kwargs):
            raise subprocess.CalledProcessError(
                returncode=9,
                cmd=args,
                stderr="driver not loaded",
            )
        with self.assertRaises(gp.PreflightError) as ctx:
            gp.gpu_preflight(0, _run=_run)
        self.assertIn("exit 9", str(ctx.exception))
        self.assertIn("driver not loaded", str(ctx.exception))

    def test_malformed_gpu_output(self):
        mock_run = make_mock_run(gpu_stdout="garbage\n")
        with self.assertRaises(gp.PreflightError):
            gp.gpu_preflight(0, _run=mock_run)

    def test_malformed_apps_output(self):
        mock_run = make_mock_run(
            gpu_stdout=f"0, {GPU_0_UUID}\n",
            apps_stdout="garbage\n",
        )
        with self.assertRaises(gp.PreflightError):
            gp.gpu_preflight(0, _run=mock_run)

    def test_non_integer_device_index(self):
        with self.assertRaises(TypeError):
            gp.gpu_preflight("0")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            gp.gpu_preflight(True)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
