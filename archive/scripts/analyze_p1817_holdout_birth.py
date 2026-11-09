#!/usr/bin/env python3
"""Fixed evaluator for the amended P1817 holdout-birth pilot.

Classification: auxiliary/development evaluator. Decision rule is frozen by
research/P1817_PILOT_AMENDMENT_20261105.md section 3 and must not change after
outputs exist. Repaired for findings 3, 4, 5, 7 and 8 of
runs/p1817_repair_20261105/codex-integrated-review.md. Everything fails closed:
a missing, malformed or unverifiable record can never yield a pass.

Order of operations (enforced)
------------------------------
  1. Artifacts only (no image opened): validate the prefix, control_r1,
     control_r2, holdout and invariance manifests and archives (exact schemas,
     file/content hashes, contract constants, provenance, RNG content, shared
     prefix/pool, birth reconstruction, selection rule, finiteness). Recompute
     every invariance check from persisted measurements and bind the
     invariance scores/selection to the actual holdout. Validate timing.
  2. Only if step 1 found no problem: verify the noisy file hash, decode it and
     recompute ``ab_hash`` and ``trainer_target_hash`` (normal and C-perturbed)
     on CPU; require equality with every artifact.
  3. Only if step 2 found no problem: open, hash-verify and decode the
     evaluator-only clean truth; compute per-arm metrics and apply the rule.

Outcomes: ``invalid`` (leakage, violated matching/contract/provenance, or a
self-contradicting record), ``inconclusive`` (missing/failed/corrupt artifacts,
measurement failure, unverified reproducibility or unbound evidence),
``no_go`` (complete valid comparison failing an improvement criterion),
``preliminary_pass``. Only the last is a pass. B-fold MSE is descriptive only.
Two control repeats give a minimal observed floor, not a confidence interval,
and say nothing about holdout variance.

REQUIRED ARTIFACT FIELDS (producer contract; items marked NEW are not yet
emitted by scripts/p1817_holdout_birth_pilot.py and must be added there)
---------------------------------------------------------------------------
Every manifest (prefix, arms, invariance):
  * existing v2 fields: artifact_format, kind, status == "completed", seed,
    input_sha256 (== verified noisy hash), source_commit, source_license
    == "MIT", initial_gaussians, final_gaussians, birth_step, birth_count,
    candidate_pool_size, max_steps, device ("cpu" | "cuda" | "cuda:N"),
    versions (non-empty str python/torch/numpy/platform/hostname, plus
    cuda/cuda_device_name on CUDA), command (list of str; must contain the
    subcommand: "prefix" | "continue" + arm name | "invariance"),
    pilot_script_sha256 (64 lowercase hex).
  * NEW fold_helper_sha256: SHA-256 of the p1817_fold_boundary.py the producer
    imported; must equal the helper this evaluator imports.
  * NEW implementation_config: ``vars(_build_base_args(...))`` minus
    IMPLEMENTATION_CONFIG_EXCLUDED_KEYS; must equal
    EXPECTED_IMPLEMENTATION_CONFIG exactly (types included).
  * NEW process_started_unix: time.time() at interpreter start, before heavy
    imports, lock acquisition and prefix loading.
  * finished_unix: time.time() after every archive is written and hashed,
    immediately before the manifest write (current ``_guarded`` placement).
  * NEW timing_sec.process_wall: monotonic seconds over the same span; must
    agree with finished_unix - process_started_unix within
    max(TIMING_CLOCK_TOLERANCE_SEC, TIMING_CLOCK_TOLERANCE_REL * wall) and be
    >= the phase compute wall. Phases must not overlap in time.
  * provenance keys PROVENANCE_KEYS must be identical across all five.
Prefix: steps_completed == 500, fold_counts, ab_hash, trainer_target_hash
  (64 hex), timing_sec {init, train_1_500, pool, prefix_wall}; files exactly
  PREFIX_FILES. rng_* archives must follow RNG_FIXED_SCHEMA (the
  ``capture_rng_state`` layout) with cuda_0..cuda_{n-1}; the pool draw must
  have advanced numpy and the execution-device torch generator and left
  python random and the other torch generators unchanged.
Arm: arm, role, prefix_ref, ab_hash, trainer_target_hash, steps_completed,
  num_gaussians_final, timing_sec {setup, selection_and_birth,
  continuation_501_1000, finalize_render, arm_wall}; files exactly ARM_FILES.
  NEW rng_continuation_start: ``capture_rng_state()`` immediately after
  ``restore_rng_state(prefix rng_after_pool)``; must be identical to it.
Invariance (only a ``passed`` record can support a pass): prefix_ref,
  invariance_result, checks (exactly the INVARIANCE_CHECKS names; NEW names
  replace forward_repeat_bitwise_stable/forward_equal_across_models),
  timing_sec {invariance_wall}, and NEW:
  * cpu_ab_hash {normal, cperturb}; trainer_target_hash_by_c {normal, cperturb}
  * forward_sha256 {base: {normal_1, normal_2, cperturb_1, cperturb_2},
    augmented: {same keys}} -- 64-hex hashes of raw forward outputs; augmented
    = the 257-Gaussian renders of every pool candidate in pool order.
  * files exactly INVARIANCE_FILES: ``scores`` with float64 (256,)
    scores_normal_1/_2, scores_cperturb and int64 (64,) selected_normal_1/_2,
    selected_cperturb; ``pool_recompute_{normal,cperturb}`` (candidate-pool
    schema); ``rng_after_pool_recompute_{normal,cperturb}`` (RNG captured
    after rebuilding the pool from rng_before_pool).
  The evaluator recomputes every check; recorded checks/result must agree.
  scores_normal_1 must be bitwise identical to the holdout scores and
  selected_normal_1 identical to the holdout selection.

CLI exit codes: EXIT_CODES (0 preliminary_pass, 10 no_go, 20 inconclusive,
30 invalid), EXIT_OUTPUT_REFUSED (40: output exists/unwritable; nothing
evaluated), EXIT_EVALUATOR_ERROR (50: evaluator crashed; report says so).
argparse usage errors exit 2. Only exit 0 may be treated as a pass.

numpy + PIL + the CPU fold helpers only; no torch, no upstream import.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p1817_fold_boundary as _fold  # noqa: E402
from p1817_fold_boundary import (  # noqa: E402
    fold_flat_indices,
    hash_ab_values,
    perturb_c_only,
    split_ab_values,
    validate_proposal_indices,
)

# Frozen constants (contract 2026-11-04 / amendment 2026-11-05).
ARTIFACT_FORMAT = "p1817-holdout-birth-artifact-v2"
_ARRAY_HASH_DOMAIN = b"P1817-holdout-birth-arrays-v2"
EXPECTED_NOISY_SHA256 = "af17835d24f94488fa042efbfda00aa21628b5c0f299835404c75e7e359b0632"
EXPECTED_CLEAN_SHA256 = "91a7824e38717f2fbece5af0705a8c50ca8aa3057b7d268bc6e1eee86c37e1c5"
EXPECTED_UPSTREAM_COMMIT = "03088368d42684fb54225c981cfd94b58cc0393a"
EXPECTED_SOURCE_LICENSE = "MIT"
SEED = 123
H = W = 192
N_INIT, N_FINAL, K, POOL, BIRTH_STEP, MAX_STEPS = 256, 320, 64, 256, 500, 1000
INIT_SCALE = 5.0
PARAM_KEYS = ("xy", "scale", "rot", "feat", "vis_feat")
PARAM_COLS = {"xy": 2, "scale": 2, "rot": 1, "feat": 3, "vis_feat": 3}
ARMS = {"control_r1": "control", "control_r2": "control", "holdout": "holdout"}
PHASES = ("prefix", "control_r1", "control_r2", "holdout", "invariance")
PREFIX_FILES = ("prefix_params", "candidate_pool", "rng_before_pool", "rng_after_pool")
ARM_FILES = ("selection", "birth_params", "final_params", "final_render",
             "rng_continuation_start")
INVARIANCE_FILES = ("scores", "pool_recompute_normal", "pool_recompute_cperturb",
                    "rng_after_pool_recompute_normal", "rng_after_pool_recompute_cperturb")
C_VARIANTS = ("normal", "cperturb")
FORWARD_RUNS = ("normal_1", "normal_2", "cperturb_1", "cperturb_2")
INV_SCORE_RUNS = ("normal_1", "normal_2", "cperturb")
INVALID, INCONCLUSIVE = "invalid", "inconclusive"

# Implementation configuration frozen by _build_base_args in the pilot.
IMPLEMENTATION_CONFIG_EXCLUDED_KEYS = ("device", "log_dir", "data_root", "input_path",
                                       "pilot_variant")
EXPECTED_IMPLEMENTATION_CONFIG = {
    "seed": 123, "eval": False, "render_height": 2048,
    "quantize": False, "pos_bits": 32, "scale_bits": 32, "rot_bits": 32, "feat_bits": 32,
    "log_level": "INFO", "save_image_format": "png", "save_plot_format": "png",
    "vis_gaussians": False, "save_image_steps": 100_000, "save_ckpt_steps": 100_000,
    "eval_steps": 100,
    "gamma": 1.0, "downsample": False, "downsample_ratio": 2.0,
    "num_gaussians": 320, "init_scale": 5.0, "topk": 10, "disable_topk_norm": False,
    "disable_inverse_scale": False, "ckpt_file": "", "disable_color_init": True,
    "init_mode": "random", "init_random_ratio": 1.0, "smap_filter_size": 20,
    "l1_loss_ratio": 0.0, "l2_loss_ratio": 1.0, "ssim_loss_ratio": 0.0,
    "disable_tiles": False, "max_steps": 1000, "pos_lr": 5.0e-4, "scale_lr": 2.0e-3,
    "rot_lr": 2.0e-3, "feat_lr": 5.0e-3, "disable_lr_schedule": True,
    "decay_ratio": 10.0, "check_decay_steps": 1000, "max_decay_times": 1,
    "decay_threshold": 1e-3,
    "disable_prog_optim": False, "initial_ratio": 256 / 320, "add_steps": 500,
    "add_times": 1, "post_min_steps": 500,
}
PROVENANCE_KEYS = ("pilot_script_sha256", "fold_helper_sha256", "source_commit",
                   "source_license", "device", "versions", "implementation_config")
REQUIRED_VERSION_KEYS = ("python", "torch", "numpy", "platform", "hostname")
CUDA_VERSION_KEYS = ("cuda", "cuda_device_name")

# RNG record layout of capture_rng_state(). Byte sizes are pinned to the
# torch 2.x CPU MT19937 (5056 B) and CUDA Philox (16 B) generator states; a
# different layout fails closed as inconclusive.
TORCH_CPU_RNG_BYTES = 5056
CUDA_RNG_BYTES = 16
MAX_CUDA_DEVICES = 64
RNG_FIXED_SCHEMA = {
    "np_keys": (np.uint32, (624,)), "np_pos": (np.int64, ()),
    "np_has_gauss": (np.int64, ()), "np_cached_gaussian": (np.float64, ()),
    "py_version": (np.int64, ()), "py_internal": (np.int64, (625,)),
    "py_gauss_is_none": (np.bool_, ()), "py_gauss_next": (np.float64, ()),
    "torch_cpu": (np.uint8, (TORCH_CPU_RNG_BYTES,)), "cuda_count": (np.int64, ()),
}
_NP_RNG_KEYS = ("np_keys", "np_pos", "np_has_gauss", "np_cached_gaussian")
_PY_RNG_KEYS = ("py_version", "py_internal", "py_gauss_is_none", "py_gauss_next")

# Invariance check names and the frozen classification rule (amendment item 2).
LEAK_CHECKS = ("cpu_ab_hash_equal_across_c", "trainer_target_hash_equal_across_c")
REPRO_CHECKS = ("cpu_ab_hash_matches_prefix", "trainer_target_hash_matches_prefix",
                "base_forward_repeat_bitwise_stable", "augmented_forward_repeat_bitwise_stable",
                "base_forward_equal_across_models", "augmented_forward_equal_across_models",
                "pool_recompute_matches_saved", "rng_after_recompute_matches_saved",
                "scorer_repeat_bitwise_stable")
LEAK_AFTER_REPRO_CHECKS = ("pool_recompute_equal_across_c", "rng_after_recompute_equal_across_c",
                           "scores_equal_across_c", "selection_equal_across_c")
INVARIANCE_CHECKS = LEAK_CHECKS + REPRO_CHECKS + LEAK_AFTER_REPRO_CHECKS

# Timing.
PHASE_TIMING_KEYS = {
    "prefix": (("init", "train_1_500", "pool", "prefix_wall"), "prefix_wall"),
    "arm": (("setup", "selection_and_birth", "continuation_501_1000", "finalize_render",
             "arm_wall"), "arm_wall"),
    "invariance": (("invariance_wall",), "invariance_wall"),
}
TIMING_CLOCK_TOLERANCE_SEC = 1.0
TIMING_CLOCK_TOLERANCE_REL = 0.01
TIMING_EPS = 1e-6

# Contract documents whose identities are recorded in every report.
REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOCUMENTS = {
    "contract_20261104": REPO_ROOT / "research" / "P1817_HOLDOUT_BIRTH_PILOT_CONTRACT_20261104.md",
    "amendment_20261105": REPO_ROOT / "research" / "P1817_PILOT_AMENDMENT_20261105.md",
}

# CLI exit semantics.
EXIT_CODES = {"preliminary_pass": 0, "no_go": 10, INCONCLUSIVE: 20, INVALID: 30}
EXIT_OUTPUT_REFUSED = 40
EXIT_EVALUATOR_ERROR = 50
RESERVATION_RECORD = {"report_status": "reserved_incomplete", "decision": None,
                      "note": "Evaluation in progress or interrupted. Not a result."}

_HEX64 = re.compile(r"[0-9a-f]{64}")


class ArtifactProblem(Exception):
    def __init__(self, category: str, where: str, message: str):
        super().__init__(f"[{category}] {where}: {message}")
        self.category, self.where, self.message = category, where, message


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_arrays_hash(arrays: Dict[str, np.ndarray]) -> str:
    """Must match ``canonical_arrays_hash`` in p1817_holdout_birth_pilot.py."""
    h = hashlib.sha256()
    h.update(_ARRAY_HASH_DOMAIN)
    for key in sorted(arrays):
        arr = np.ascontiguousarray(np.asarray(arrays[key]))
        h.update(f"|{key}:{arr.dtype.str}:{tuple(arr.shape)}|".encode("ascii"))
        h.update(arr.tobytes())
    return h.hexdigest()


def trainer_target_sha256(image_chw: np.ndarray) -> str:
    """Recompute the pilot's ``trainer_target_hash`` from a verified image.

    Mirrors pilot ``_load_target_images`` + ``_sha256_tensor``: a float32
    (3, H, W) array that is NaN everywhere except the A/B values, hashed as
    raw C-order bytes (no domain prefix).
    """
    ab = split_ab_values(image_chw)
    safe = np.full(np.shape(image_chw), np.nan, dtype=np.float32)
    flat = safe.reshape(safe.shape[0], -1)
    flat[:, ab.a_index] = ab.a_values
    flat[:, ab.b_index] = ab.b_values
    return hashlib.sha256(np.ascontiguousarray(safe).tobytes()).hexdigest()


def fold_helper_sha256() -> str:
    return sha256_file(Path(_fold.__file__).resolve())


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _is_hex64(v) -> bool:
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _device_index(device, where: str) -> Optional[int]:
    if device == "cpu":
        return None
    match = re.fullmatch(r"cuda(?::(\d+))?", device) if isinstance(device, str) else None
    if match is None:
        raise ArtifactProblem(INCONCLUSIVE, where, f"unsupported device {device!r}")
    return int(match.group(1) or 0)


# ---------------------------------------------------------------------------
# Artifact reading
# ---------------------------------------------------------------------------
def _manifest(run_dir: Path, kind: str, where: str, expected_noisy_sha: str) -> Dict:
    path = run_dir / "manifest.json"
    if not path.is_file():
        raise ArtifactProblem(INCONCLUSIVE, where, "missing manifest (run absent or unfinished)")
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ArtifactProblem(INCONCLUSIVE, where, f"unreadable manifest: {exc!r}")
    if not isinstance(m, dict) or m.get("artifact_format") != ARTIFACT_FORMAT:
        raise ArtifactProblem(INCONCLUSIVE, where, "unknown artifact format")
    if m.get("status") != "completed":
        raise ArtifactProblem(INCONCLUSIVE, where,
                              f"status={m.get('status')!r} error={m.get('error')!r}")
    if m.get("kind") != kind:
        raise ArtifactProblem(INVALID, where, f"kind {m.get('kind')!r} != {kind!r}")
    contract = {"seed": SEED, "input_sha256": expected_noisy_sha,
                "source_commit": EXPECTED_UPSTREAM_COMMIT,
                "source_license": EXPECTED_SOURCE_LICENSE, "initial_gaussians": N_INIT,
                "final_gaussians": N_FINAL, "birth_step": BIRTH_STEP, "birth_count": K,
                "candidate_pool_size": POOL, "max_steps": MAX_STEPS}
    for key, val in contract.items():
        if key not in m:
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing contract field {key}")
        if _canon(m[key]) != _canon(val):
            raise ArtifactProblem(INVALID, where, f"contract field {key}={m[key]!r} != {val!r}")
    # Provenance (finding 5).
    for key in ("pilot_script_sha256", "fold_helper_sha256"):
        if not _is_hex64(m.get(key)):
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing or malformed {key}")
    if m["fold_helper_sha256"] != fold_helper_sha256():
        raise ArtifactProblem(INVALID, where, "fold helper differs from the evaluator's helper")
    device = m.get("device")
    if not isinstance(device, str) or not device:
        raise ArtifactProblem(INCONCLUSIVE, where, "missing device")
    on_cuda = _device_index(device, where) is not None
    versions = m.get("versions")
    need = REQUIRED_VERSION_KEYS + (CUDA_VERSION_KEYS if on_cuda else ())
    if not isinstance(versions, dict) or not all(
            isinstance(versions.get(k), str) and versions[k] for k in need):
        raise ArtifactProblem(INCONCLUSIVE, where, "missing hardware/software versions")
    cmd = m.get("command")
    if not isinstance(cmd, list) or not cmd or not all(isinstance(c, str) for c in cmd):
        raise ArtifactProblem(INCONCLUSIVE, where, "missing command record")
    cfg = m.get("implementation_config")
    if not isinstance(cfg, dict):
        raise ArtifactProblem(INCONCLUSIVE, where, "missing implementation_config")
    if _canon(cfg) != _canon(EXPECTED_IMPLEMENTATION_CONFIG):
        raise ArtifactProblem(INVALID, where, "implementation_config differs from frozen config")
    m["_manifest_sha256"] = sha256_file(path)
    return m


def _check_command(m: Dict, tokens: Sequence[str], where: str) -> None:
    if not all(t in m["command"] for t in tokens):
        raise ArtifactProblem(INVALID, where, f"command {m['command']!r} lacks {list(tokens)}")


def _files(run_dir: Path, m: Dict, names, where: str) -> Dict[str, Dict[str, np.ndarray]]:
    out = {}
    entries = m.get("files")
    if not isinstance(entries, dict):
        raise ArtifactProblem(INCONCLUSIVE, where, "manifest lacks file table")
    extra = set(entries) - set(names)
    if extra:
        raise ArtifactProblem(INVALID, where, f"unexpected file entries {sorted(extra)}")
    for name in names:
        e = entries.get(name)
        if not isinstance(e, dict) or not {"file", "sha256", "content_hash"} <= set(e):
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing file entry {name}")
        if e["file"] != f"{name}.npz":
            raise ArtifactProblem(INVALID, where, f"file entry {name} names {e['file']!r}")
        if not (_is_hex64(e["sha256"]) and _is_hex64(e["content_hash"])):
            raise ArtifactProblem(INCONCLUSIVE, where, f"malformed hashes for {name}")
        path = run_dir / e["file"]
        if not path.is_file():
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing file {e['file']}")
        if sha256_file(path) != e["sha256"]:
            raise ArtifactProblem(INCONCLUSIVE, where, f"file hash mismatch {e['file']}")
        try:
            with np.load(path, allow_pickle=False) as data:
                arrays = {k: data[k].copy() for k in data.files}
        except Exception as exc:  # corrupt archive
            raise ArtifactProblem(INCONCLUSIVE, where, f"unreadable {e['file']}: {exc!r}")
        if canonical_arrays_hash(arrays) != e["content_hash"]:
            raise ArtifactProblem(INCONCLUSIVE, where, f"content hash mismatch {e['file']}")
        out[name] = arrays
    return out


def _exact_keys(arrays: Dict, expected, where: str, label: str) -> None:
    if set(arrays) != set(expected):
        raise ArtifactProblem(INVALID, where,
                              f"{label} keys {sorted(arrays)} != {sorted(expected)}")


def _check_params(arrays: Dict[str, np.ndarray], n: int, where: str, label: str) -> None:
    for k in PARAM_KEYS:
        a = arrays.get(k)
        if a is None or a.dtype != np.float32 or a.shape != (n, PARAM_COLS[k]):
            raise ArtifactProblem(INVALID, where, f"{label}.{k} has wrong dtype/shape")
        if not np.isfinite(a).all():
            raise ArtifactProblem(INCONCLUSIVE, where, f"{label}.{k} non-finite")


def _check_pool(pool: Dict[str, np.ndarray], where: str, label: str) -> np.ndarray:
    _exact_keys(pool, PARAM_KEYS + ("indices",), where, label)
    if pool["indices"].dtype != np.int64:
        raise ArtifactProblem(INVALID, where, f"{label}.indices is not int64")
    try:
        idx = validate_proposal_indices(pool["indices"], H, W, expected_count=POOL)
    except (TypeError, ValueError) as exc:
        raise ArtifactProblem(INVALID, where, f"{label} indices: {exc}")
    _check_params(pool, POOL, where, label)
    # Provenance: candidate positions are the A pixel centres; scale/rot fixed.
    expected_xy = np.stack([(idx % W + 0.5) / W, (idx // W + 0.5) / H], axis=1)
    if np.max(np.abs(pool["xy"].astype(np.float64) - expected_xy)) > 1e-5:
        raise ArtifactProblem(INVALID, where, f"{label} xy do not match pool pixel indices")
    if not (np.all(pool["scale"] == np.float32(1.0 / INIT_SCALE)) and np.all(pool["rot"] == 0)):
        raise ArtifactProblem(INVALID, where, f"{label} scale/rot are not the frozen initial values")
    return idx


def validate_rng_state(state: Dict[str, np.ndarray], device: str, where: str, label: str) -> None:
    """Strict schema and content check of one ``capture_rng_state`` record (finding 4)."""
    def bad(msg):
        return ArtifactProblem(INCONCLUSIVE, where, f"{label}: {msg}")

    if not isinstance(state, dict):
        raise bad("not an array record")
    for key, (dtype, shape) in RNG_FIXED_SCHEMA.items():
        a = state.get(key)
        if a is None or a.dtype != np.dtype(dtype) or a.shape != shape:
            raise bad(f"{key} missing or wrong dtype/shape")
    n = int(state["cuda_count"])
    if not 0 <= n <= MAX_CUDA_DEVICES:
        raise bad(f"cuda_count {n} out of range")
    if set(state) != set(RNG_FIXED_SCHEMA) | {f"cuda_{i}" for i in range(n)}:
        raise bad(f"unexpected key set {sorted(state)}")
    for i in range(n):
        a = state[f"cuda_{i}"]
        if a.dtype != np.uint8 or a.shape != (CUDA_RNG_BYTES,):
            raise bad(f"cuda_{i} wrong dtype/shape")
    if not state["np_keys"].any():
        raise bad("all-zero MT19937 key")
    if not 0 <= int(state["np_pos"]) <= 624:
        raise bad("numpy position out of range")
    has_gauss, cached = int(state["np_has_gauss"]), float(state["np_cached_gaussian"])
    if has_gauss not in (0, 1) or not math.isfinite(cached) or (has_gauss == 0 and cached != 0.0):
        raise bad("inconsistent numpy gaussian cache")
    if int(state["py_version"]) != 3:
        raise bad("python random state version != 3")
    words, py_pos = state["py_internal"][:624], int(state["py_internal"][624])
    if words.min() < 0 or words.max() > 0xFFFFFFFF or not words.any() or not 0 <= py_pos <= 624:
        raise bad("python MT19937 state out of range")
    nxt = float(state["py_gauss_next"])
    if not math.isfinite(nxt) or (bool(state["py_gauss_is_none"]) and nxt != 0.0):
        raise bad("inconsistent python gauss_next")
    dev = _device_index(device, where)
    if dev is not None and dev >= n:
        raise bad(f"no saved CUDA state for execution device {device}")


def _same(a: Dict, b: Dict, keys) -> bool:
    return all(np.array_equal(a[k], b[k]) for k in keys)


def _check_pool_rng_transition(before: Dict, after: Dict, device: str, where: str) -> None:
    """Pool construction draws numpy choice + on-device rand_like only."""
    def bad(msg):
        return ArtifactProblem(INCONCLUSIVE, where, f"rng across pool construction: {msg}")

    if _same(before, after, _NP_RNG_KEYS):
        raise bad("numpy state not advanced by the pool draw")
    if not _same(before, after, _PY_RNG_KEYS):
        raise bad("python random state changed")
    if int(before["cuda_count"]) != int(after["cuda_count"]):
        raise bad("CUDA generator count changed")
    cuda_keys = [f"cuda_{i}" for i in range(int(before["cuda_count"]))]
    dev = _device_index(device, where)
    if dev is None:
        if _same(before, after, ("torch_cpu",)) or not _same(before, after, cuda_keys):
            raise bad("torch generators inconsistent with a CPU vis_feat draw")
    else:
        own = f"cuda_{dev}"
        if (not _same(before, after, ("torch_cpu",)) or _same(before, after, (own,))
                or not _same(before, after, [k for k in cuda_keys if k != own])):
            raise bad("torch generators inconsistent with an on-device vis_feat draw")


def validate_prefix(run_root: Path, expected_noisy_sha: str = EXPECTED_NOISY_SHA256) -> Dict:
    where = "prefix"
    run_dir = run_root / "prefix"
    m = _manifest(run_dir, "prefix", where, expected_noisy_sha)
    _check_command(m, ("prefix",), where)
    f = _files(run_dir, m, PREFIX_FILES, where)
    if m.get("steps_completed") != BIRTH_STEP:
        raise ArtifactProblem(INVALID, where, "prefix did not stop at the birth step")
    expected_counts = {k: int(v.size) for k, v in fold_flat_indices(H, W).items()}
    if "fold_counts" not in m:
        raise ArtifactProblem(INCONCLUSIVE, where, "missing fold_counts")
    if _canon(m["fold_counts"]) != _canon(expected_counts):
        raise ArtifactProblem(INVALID, where, "fold_counts differ from the frozen fold map")
    _exact_keys(f["prefix_params"], PARAM_KEYS, where, "prefix_params")
    _check_params(f["prefix_params"], N_INIT, where, "prefix_params")
    _check_pool(f["candidate_pool"], where, "candidate_pool")
    for key in ("ab_hash", "trainer_target_hash"):
        if not _is_hex64(m.get(key)):
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing or malformed {key}")
    for label in ("rng_before_pool", "rng_after_pool"):
        validate_rng_state(f[label], m["device"], where, label)
    _check_pool_rng_transition(f["rng_before_pool"], f["rng_after_pool"], m["device"], where)
    ref = {
        "manifest_sha256": m["_manifest_sha256"],
        "prefix_params_hash": canonical_arrays_hash(f["prefix_params"]),
        "candidate_pool_hash": canonical_arrays_hash(f["candidate_pool"]),
        "rng_before_pool_hash": canonical_arrays_hash(f["rng_before_pool"]),
        "rng_after_pool_hash": canonical_arrays_hash(f["rng_after_pool"]),
    }
    return {"manifest": m, "files": f, "ref": ref}


def _check_prefix_ref(m: Dict, prefix: Dict, where: str) -> None:
    got = m.get("prefix_ref")
    if not isinstance(got, dict):
        raise ArtifactProblem(INVALID, where, "missing prefix_ref")
    for key, val in prefix["ref"].items():
        if got.get(key) != val:
            raise ArtifactProblem(INVALID, where, f"prefix_ref.{key} differs from shared prefix")


def _check_selection(sel, where: str, label: str) -> None:
    if (sel is None or sel.dtype != np.int64 or sel.shape != (K,)
            or np.unique(sel).size != K or sel.min() < 0 or sel.max() >= POOL):
        raise ArtifactProblem(INVALID, where, f"malformed {label}")


def _top_k(scores: np.ndarray) -> np.ndarray:
    return np.argsort(-scores, kind="stable")[:K]


def validate_arm(run_root: Path, arm: str, prefix: Dict,
                 expected_noisy_sha: str = EXPECTED_NOISY_SHA256) -> Dict:
    where = arm
    run_dir = run_root / arm
    m = _manifest(run_dir, "arm", where, expected_noisy_sha)
    role = ARMS[arm]
    if m.get("arm") != arm or m.get("role") != role:
        raise ArtifactProblem(INVALID, where, "arm/role label mismatch")
    _check_command(m, ("continue", arm), where)
    _check_prefix_ref(m, prefix, where)
    pm = prefix["manifest"]
    if m.get("ab_hash") != pm["ab_hash"] or m.get("trainer_target_hash") != pm["trainer_target_hash"]:
        raise ArtifactProblem(INVALID, where, "trainer inputs differ from prefix")
    if m.get("steps_completed") != MAX_STEPS or m.get("num_gaussians_final") != N_FINAL:
        raise ArtifactProblem(INVALID, where, "steps or final K differ from contract")
    f = _files(run_dir, m, ARM_FILES, where)

    _exact_keys(f["selection"], ("selected", "scores"), where, "selection")
    sel, scores = f["selection"]["selected"], f["selection"]["scores"]
    _check_selection(sel, where, "selected indices")
    if scores.dtype != np.float64:
        raise ArtifactProblem(INVALID, where, "selection scores are not float64")
    if role == "control":
        if not np.array_equal(sel, np.arange(K)) or scores.shape != (0,):
            raise ArtifactProblem(INVALID, where, "control did not take the first 64")
    else:
        if scores.shape != (POOL,) or not np.isfinite(scores).all():
            raise ArtifactProblem(INVALID, where, "holdout scores missing or non-finite")
        if not np.array_equal(sel, _top_k(scores)):
            raise ArtifactProblem(INVALID, where, "holdout selection is not stable top-64")

    birth = f["birth_params"]
    _exact_keys(birth, PARAM_KEYS, where, "birth_params")
    _check_params(birth, N_FINAL, where, "birth_params")
    pre, pool = prefix["files"]["prefix_params"], prefix["files"]["candidate_pool"]
    for k in PARAM_KEYS:
        if not (np.array_equal(birth[k][:N_INIT], pre[k]) and np.array_equal(birth[k][N_INIT:], pool[k][sel])):
            raise ArtifactProblem(INVALID, where, f"birth_params.{k} is not prefix + pool[selected]")
    _exact_keys(f["final_params"], PARAM_KEYS, where, "final_params")
    _check_params(f["final_params"], N_FINAL, where, "final_params")
    _exact_keys(f["final_render"], ("render",), where, "final_render")
    render = f["final_render"]["render"]
    if render.shape != (3, H, W) or render.dtype != np.float32:
        raise ArtifactProblem(INVALID, where, "final render has wrong shape/dtype")
    if not np.isfinite(render).all():
        raise ArtifactProblem(INCONCLUSIVE, where, "final render non-finite")
    rng_start = f["rng_continuation_start"]
    validate_rng_state(rng_start, m["device"], where, "rng_continuation_start")
    if canonical_arrays_hash(rng_start) != prefix["ref"]["rng_after_pool_hash"]:
        raise ArtifactProblem(INVALID, where, "continuation-start RNG differs from prefix rng_after_pool")
    return {"manifest": m, "render": render, "selected": sel, "scores": scores,
            "peak_vram_bytes": m.get("peak_vram_bytes")}


def _hash_map(m: Dict, key: str, names, where: str) -> Dict[str, str]:
    v = m.get(key)
    if not isinstance(v, dict) or set(v) != set(names) or not all(_is_hex64(v[n]) for n in names):
        raise ArtifactProblem(INCONCLUSIVE, where, f"missing or malformed {key}")
    return dict(v)


def invariance_rule(checks: Dict[str, bool]) -> str:
    """Frozen classification of recomputed invariance checks (amendment item 2)."""
    if not all(checks[k] for k in LEAK_CHECKS):
        return "failed_leakage"
    if not all(checks[k] for k in REPRO_CHECKS):
        return "inconclusive"
    if not all(checks[k] for k in LEAK_AFTER_REPRO_CHECKS):
        return "failed_leakage"
    return "passed"


def validate_invariance(run_root: Path, prefix: Dict,
                        expected_noisy_sha: str = EXPECTED_NOISY_SHA256) -> Dict:
    where = "invariance"
    run_dir = run_root / "invariance"
    m = _manifest(run_dir, "invariance", where, expected_noisy_sha)
    _check_command(m, ("invariance",), where)
    _check_prefix_ref(m, prefix, where)
    result = m.get("invariance_result")
    if result == "failed_leakage":
        raise ArtifactProblem(INVALID, where, f"C-invariance leakage reported: {m.get('checks')}")
    if result != "passed":
        raise ArtifactProblem(INCONCLUSIVE, where, f"invariance result {result!r}: {m.get('checks')}")

    # A "passed" record must carry the measurements behind every check (finding 3).
    cab = _hash_map(m, "cpu_ab_hash", C_VARIANTS, where)
    tth = _hash_map(m, "trainer_target_hash_by_c", C_VARIANTS, where)
    fwd = m.get("forward_sha256")
    if not isinstance(fwd, dict) or set(fwd) != {"base", "augmented"}:
        raise ArtifactProblem(INCONCLUSIVE, where, "missing forward_sha256 base/augmented")
    base = _hash_map(fwd, "base", FORWARD_RUNS, where)
    aug = _hash_map(fwd, "augmented", FORWARD_RUNS, where)
    f = _files(run_dir, m, INVARIANCE_FILES, where)
    sc = f["scores"]
    _exact_keys(sc, [f"scores_{r}" for r in INV_SCORE_RUNS] + [f"selected_{r}" for r in INV_SCORE_RUNS],
                where, "scores")
    for r in INV_SCORE_RUNS:
        s, sel = sc[f"scores_{r}"], sc[f"selected_{r}"]
        if s.dtype != np.float64 or s.shape != (POOL,):
            raise ArtifactProblem(INVALID, where, f"scores_{r} wrong dtype/shape")
        if not np.isfinite(s).all():
            raise ArtifactProblem(INCONCLUSIVE, where, f"scores_{r} non-finite")
        _check_selection(sel, where, f"selected_{r}")
        if not np.array_equal(sel, _top_k(s)):
            raise ArtifactProblem(INVALID, where, f"selected_{r} is not stable top-64 of scores_{r}")
    pool_h, rng_h = {}, {}
    for v in C_VARIANTS:
        _check_pool(f[f"pool_recompute_{v}"], where, f"pool_recompute_{v}")
        validate_rng_state(f[f"rng_after_pool_recompute_{v}"], m["device"], where,
                           f"rng_after_pool_recompute_{v}")
        pool_h[v] = canonical_arrays_hash(f[f"pool_recompute_{v}"])
        rng_h[v] = canonical_arrays_hash(f[f"rng_after_pool_recompute_{v}"])

    pm, ref = prefix["manifest"], prefix["ref"]
    s_n1, s_n2, s_p = (sc[f"scores_{r}"] for r in INV_SCORE_RUNS)
    checks = {
        "cpu_ab_hash_equal_across_c": cab["normal"] == cab["cperturb"],
        "trainer_target_hash_equal_across_c": tth["normal"] == tth["cperturb"],
        "cpu_ab_hash_matches_prefix": cab["normal"] == pm["ab_hash"],
        "trainer_target_hash_matches_prefix": tth["normal"] == pm["trainer_target_hash"],
        "base_forward_repeat_bitwise_stable": (base["normal_1"] == base["normal_2"]
                                               and base["cperturb_1"] == base["cperturb_2"]),
        "augmented_forward_repeat_bitwise_stable": (aug["normal_1"] == aug["normal_2"]
                                                    and aug["cperturb_1"] == aug["cperturb_2"]),
        "base_forward_equal_across_models": base["normal_1"] == base["cperturb_1"],
        "augmented_forward_equal_across_models": aug["normal_1"] == aug["cperturb_1"],
        "pool_recompute_matches_saved": pool_h["normal"] == ref["candidate_pool_hash"],
        "rng_after_recompute_matches_saved": rng_h["normal"] == ref["rng_after_pool_hash"],
        "scorer_repeat_bitwise_stable": (s_n1.tobytes() == s_n2.tobytes() and np.array_equal(
            sc["selected_normal_1"], sc["selected_normal_2"])),
        "pool_recompute_equal_across_c": pool_h["normal"] == pool_h["cperturb"],
        "rng_after_recompute_equal_across_c": rng_h["normal"] == rng_h["cperturb"],
        "scores_equal_across_c": s_n1.tobytes() == s_p.tobytes(),
        "selection_equal_across_c": bool(np.array_equal(sc["selected_normal_1"],
                                                        sc["selected_cperturb"])),
    }
    recorded = m.get("checks")
    if not isinstance(recorded, dict):
        raise ArtifactProblem(INCONCLUSIVE, where, "missing recorded checks")
    if _canon(recorded) != _canon(checks):
        raise ArtifactProblem(INVALID, where,
                              "recorded checks contradict persisted measurements: "
                              f"recomputed {checks}")
    recomputed = invariance_rule(checks)
    if recomputed != "passed":
        raise ArtifactProblem(INVALID, where, f"record claims passed; measurements give {recomputed}")
    return {"manifest": m, "scores": s_n1, "selected": sc["selected_normal_1"],
            "cpu_ab_hash": cab, "trainer_target_hash_by_c": tth, "checks": checks}


def check_cross_provenance(manifests: Dict[str, Dict]) -> None:
    """All phases must share one implementation, device and environment."""
    ref = manifests["prefix"]
    for name, m in manifests.items():
        for key in PROVENANCE_KEYS:
            if _canon(m[key]) != _canon(ref[key]):
                raise ArtifactProblem(INVALID, name, f"{key} differs from prefix")


def bind_invariance_to_holdout(invariance: Dict, holdout: Dict) -> None:
    """The invariance evidence must concern the holdout's actual scores/selection."""
    hs, inv = holdout["scores"], invariance["scores"]
    if hs.dtype != inv.dtype or hs.shape != inv.shape or hs.tobytes() != inv.tobytes():
        raise ArtifactProblem(INCONCLUSIVE, "invariance",
                              "invariance scores are not bitwise identical to holdout scores")
    if not np.array_equal(holdout["selected"], invariance["selected"]):
        raise ArtifactProblem(INCONCLUSIVE, "invariance",
                              "invariance selection differs from holdout selection")


# ---------------------------------------------------------------------------
# Timing (finding 7)
# ---------------------------------------------------------------------------
def phase_timing(m: Dict, where: str, kind: str) -> Dict:
    keys, total_key = PHASE_TIMING_KEYS[kind]
    t = m.get("timing_sec")
    if not isinstance(t, dict):
        raise ArtifactProblem(INCONCLUSIVE, where, "missing timing_sec")
    vals = {}
    for k in keys + ("process_wall",):
        v = t.get(k)
        if not _is_number(v) or v < 0:
            raise ArtifactProblem(INCONCLUSIVE, where, f"missing or bad timing {k}={v!r}")
        vals[k] = float(v)
    process_wall = vals.pop("process_wall")
    start, finish = m.get("process_started_unix"), m.get("finished_unix")
    if not (_is_number(start) and _is_number(finish)) or finish < start:
        raise ArtifactProblem(INCONCLUSIVE, where, "missing or bad process_started_unix/finished_unix")
    if process_wall + TIMING_EPS < vals[total_key]:
        raise ArtifactProblem(INCONCLUSIVE, where, f"process_wall < {total_key}")
    tol = max(TIMING_CLOCK_TOLERANCE_SEC, TIMING_CLOCK_TOLERANCE_REL * process_wall)
    if abs((finish - start) - process_wall) > tol:
        raise ArtifactProblem(INCONCLUSIVE, where, "process_wall disagrees with wall-clock timestamps")
    return {"started_unix": float(start), "finished_unix": float(finish),
            "process_wall": process_wall, "compute": vals, "compute_total": vals[total_key]}


def check_phase_order(timings: Dict[str, Dict]) -> None:
    pre = timings["prefix"]
    for name, t in timings.items():
        if name != "prefix" and t["started_unix"] < pre["finished_unix"]:
            raise ArtifactProblem(INCONCLUSIVE, name, "phase started before the prefix finished")
    order = sorted(timings.items(), key=lambda kv: kv[1]["started_unix"])
    for (a, ta), (b, tb) in zip(order, order[1:]):
        if tb["started_unix"] < ta["finished_unix"]:
            raise ArtifactProblem(INCONCLUSIVE, b, f"overlaps {a}: phases were not serial")


def campaign_costs(timings: Dict[str, Dict], arms: Dict[str, Dict]) -> Dict:
    pre = timings["prefix"]
    span = (max(t["finished_unix"] for t in timings.values())
            - min(t["started_unix"] for t in timings.values()))
    total = sum(t["process_wall"] for t in timings.values())
    arm_walls = {a: timings[a]["process_wall"] for a in ARMS}
    return {
        "common_prefix_counted_once": {"process_wall_sec": pre["process_wall"],
                                       "compute_sec": pre["compute"]},
        "per_arm": {a: {"process_wall_sec": timings[a]["process_wall"],
                        "compute_sec": timings[a]["compute"],
                        "peak_vram_bytes": arms[a]["peak_vram_bytes"]} for a in ARMS},
        "invariance": {"process_wall_sec": timings["invariance"]["process_wall"],
                       "compute_sec": timings["invariance"]["compute"]},
        "actual_campaign_end_to_end_wall_sec": span,
        "actual_campaign_end_to_end_note": (
            "Measured wall-clock span from the first phase process start to the last "
            "phase finalization (prefix counted once, invariance included); includes "
            "gaps between processes. Attempts outside this run root are not covered."),
        "sum_of_phase_process_wall_sec": total,
        "sum_note": ("Sum of the five measured per-process walls (prefix once); "
                     "a sum, not an end-to-end measurement; excludes inter-process gaps."),
        "inter_phase_gap_sec": span - total,
        "counterfactual_standalone_cost_sec": {a: pre["process_wall"] + arm_walls[a] for a in ARMS},
        "counterfactual_note": "prefix + that arm's own process; counterfactual, not actually run",
        "wall_time_matched": len(set(arm_walls.values())) == 1,
    }


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def load_rgb8(path: Path) -> np.ndarray:
    """8-bit RGB image -> float32 CHW in [0, 1] (same scaling as upstream)."""
    from PIL import Image
    with Image.open(path) as img:
        if img.mode != "RGB":
            raise ValueError(f"Expected 8-bit RGB, got mode {img.mode}")
        arr = np.asarray(img, dtype=np.uint8)
    return (arr.astype(np.float32) / 255.0).transpose(2, 0, 1).copy()


def _check_image(img, label: str) -> None:
    if (not isinstance(img, np.ndarray) or img.dtype != np.float32 or img.shape != (3, H, W)
            or not np.isfinite(img).all() or img.min() < 0.0 or img.max() > 1.0):
        raise ArtifactProblem(INCONCLUSIVE, label, "decoded image not float32 (3,192,192) in [0,1]")


def verify_trainer_inputs(noisy: np.ndarray, prefix: Dict, arms: Dict[str, Dict],
                          invariance: Dict) -> Dict:
    """Recompute trainer-input hashes from the verified noisy image (finding 5).

    Assumes PIL's decode of the hash-verified 8-bit RGB PNG equals upstream
    ``load_images`` (cv2 BGR->RGB, uint8 -> float32 / 255, ``pow(x, 1.0)``)
    bitwise. Any disagreement fails closed as ``invalid`` (provenance not
    bound) and is never a pass.
    """
    perturbed = perturb_c_only(noisy)
    got = {"ab_hash": {"normal": hash_ab_values(split_ab_values(noisy)),
                       "cperturb": hash_ab_values(split_ab_values(perturbed))},
           "trainer_target_hash": {"normal": trainer_target_sha256(noisy),
                                   "cperturb": trainer_target_sha256(perturbed)}}
    for key, pair in got.items():
        if pair["normal"] != pair["cperturb"]:
            raise ArtifactProblem(INVALID, "noisy", f"evaluator CPU check: C-only perturbation changes {key}")
    claims = [("prefix", key, prefix["manifest"][key], got[key]["normal"])
              for key in ("ab_hash", "trainer_target_hash")]
    claims += [(a, key, arms[a]["manifest"][key], got[key]["normal"])
               for a in ARMS for key in ("ab_hash", "trainer_target_hash")]
    claims += [("invariance", f"cpu_ab_hash.{v}", invariance["cpu_ab_hash"][v], got["ab_hash"][v])
               for v in C_VARIANTS]
    claims += [("invariance", f"trainer_target_hash_by_c.{v}",
                invariance["trainer_target_hash_by_c"][v], got["trainer_target_hash"][v])
               for v in C_VARIANTS]
    for where, key, recorded, recomputed in claims:
        if recorded != recomputed:
            raise ArtifactProblem(INVALID, where,
                                  f"{key} not recomputable from the verified noisy image")
    return got


def _psnr(mse: float) -> float:
    return float("inf") if mse <= 0 else 10.0 * math.log10(1.0 / mse)


def arm_metrics(render: np.ndarray, noisy: np.ndarray, clean: np.ndarray) -> Dict[str, float]:
    pred = np.clip(render.astype(np.float64), 0.0, 1.0).reshape(3, -1)
    nz = noisy.astype(np.float64).reshape(3, -1)
    cl = clean.astype(np.float64).reshape(3, -1)
    idx = fold_flat_indices(H, W)
    out = {}
    for fold in ("A", "B", "C"):
        out[f"noisy_{fold}_mse"] = float(np.mean((pred[:, idx[fold]] - nz[:, idx[fold]]) ** 2))
    out["clean_full_mse"] = float(np.mean((pred - cl) ** 2))
    out["clean_C_mse"] = float(np.mean((pred[:, idx["C"]] - cl[:, idx["C"]]) ** 2))
    for key in list(out):
        out[key.replace("_mse", "_psnr")] = _psnr(out[key])
    return out


def _criterion(c1: float, c2: float, h: float) -> Dict:
    improvement = (c1 + c2) / 2.0 - h
    floor = abs(c1 - c2)
    return {"control_r1": c1, "control_r2": c2, "holdout": h,
            "improvement": improvement, "control_noise_floor": floor,
            "passes": bool(improvement > 0.0 and improvement > floor)}


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------
def _tool_identities() -> Dict:
    try:
        import PIL
        pil = PIL.__version__
    except Exception:  # pragma: no cover
        pil = None
    return {"evaluator_sha256": sha256_file(Path(__file__).resolve()),
            "fold_helper_path": str(Path(_fold.__file__).resolve()),
            "fold_helper_sha256": fold_helper_sha256(),
            "python": platform.python_version(), "numpy": np.__version__, "pillow": pil}


def _artifact_identity(m: Dict) -> Dict:
    return {"manifest_sha256": m["_manifest_sha256"], "command": m.get("command"),
            "files": {n: {"sha256": e["sha256"], "content_hash": e["content_hash"]}
                      for n, e in m["files"].items()}}


def evaluate(
    run_root: Path,
    noisy_path: Path,
    clean_path: Path,
    expected_noisy_sha: str = EXPECTED_NOISY_SHA256,
    expected_clean_sha: str = EXPECTED_CLEAN_SHA256,
    image_loader: Callable[[Path], np.ndarray] = load_rgb8,
) -> Dict:
    run_root = Path(run_root)
    report: Dict = {
        "classification": "auxiliary/development evaluator output; not an independent test",
        "tools": _tool_identities(),
        "contract_documents": {},
        "frozen_input_hashes_used": (expected_noisy_sha == EXPECTED_NOISY_SHA256
                                     and expected_clean_sha == EXPECTED_CLEAN_SHA256),
        "run_root": str(run_root),
        "inputs": {
            "noisy": {"path": str(noisy_path), "expected_sha256": expected_noisy_sha,
                      "sha256": None, "decoded_content_hash": None,
                      "recomputed_trainer_inputs": None},
            "clean": {"path": str(clean_path), "expected_sha256": expected_clean_sha,
                      "sha256": None, "decoded_content_hash": None},
        },
        "artifacts": {}, "implementation": None,
        "noisy_read": False, "clean_truth_read": False,
        "problems": [], "metrics": None, "criteria": None, "costs": None, "decision": None,
        "notes": ["B-fold MSE is descriptive only (biased by selection).",
                  "Control noise floor from two repeats is a minimal observed floor, "
                  "not a confidence interval; holdout variance is not estimated."],
    }
    problems: List[ArtifactProblem] = []

    def attempt(fn, *a):
        try:
            return fn(*a)
        except ArtifactProblem as p:
            problems.append(p)
        except Exception as exc:  # malformed input must never crash or pass
            problems.append(ArtifactProblem(INCONCLUSIVE, getattr(fn, "__name__", "?"),
                                            f"unexpected validation error: {exc!r}"))
        return None

    def finish(decision: Optional[str] = None) -> Dict:
        if decision is None:
            decision = INVALID if any(p.category == INVALID for p in problems) else INCONCLUSIVE
        report["problems"] = [{"category": p.category, "where": p.where, "message": p.message}
                              for p in problems]
        report["decision"] = decision
        return report

    for name, path in CONTRACT_DOCUMENTS.items():
        present = Path(path).is_file()
        report["contract_documents"][name] = {"path": str(path),
                                              "sha256": sha256_file(path) if present else None}
        if not present:
            problems.append(ArtifactProblem(INCONCLUSIVE, "contract", f"{name} document missing"))

    # --- Stage 1: artifacts only. ---
    prefix = attempt(validate_prefix, run_root, expected_noisy_sha)
    arms: Dict[str, Optional[Dict]] = {a: None for a in ARMS}
    invariance = None
    if prefix is None:
        for name in PHASES[1:]:
            problems.append(ArtifactProblem(INCONCLUSIVE, name, "not checked: prefix unavailable"))
    else:
        for arm in ARMS:
            arms[arm] = attempt(validate_arm, run_root, arm, prefix, expected_noisy_sha)
        invariance = attempt(validate_invariance, run_root, prefix, expected_noisy_sha)
    validated = {"prefix": prefix, **arms, "invariance": invariance}
    for name, v in validated.items():
        if v is not None:
            report["artifacts"][name] = _artifact_identity(v["manifest"])
    if prefix is not None:
        report["implementation"] = {k: prefix["manifest"][k] for k in PROVENANCE_KEYS}
    if all(v is not None for v in validated.values()):
        attempt(check_cross_provenance, {n: v["manifest"] for n, v in validated.items()})
        attempt(bind_invariance_to_holdout, invariance, arms["holdout"])

    timings = {}
    for name, v in validated.items():
        if v is not None:
            kind = "arm" if name in ARMS else name
            timings[name] = attempt(phase_timing, v["manifest"], name, kind)
    if len(timings) == len(PHASES) and all(timings.values()):
        attempt(check_phase_order, timings)
        report["costs"] = campaign_costs(timings, arms)

    if problems:
        return finish()

    # --- Stage 2: verified noisy image; recompute trainer inputs. ---
    try:
        if not Path(noisy_path).is_file():
            raise ArtifactProblem(INCONCLUSIVE, "noisy", "missing noisy image")
        report["noisy_read"] = True
        actual = sha256_file(Path(noisy_path))
        report["inputs"]["noisy"]["sha256"] = actual
        if actual != expected_noisy_sha:
            raise ArtifactProblem(INCONCLUSIVE, "noisy", "hash mismatch")
        noisy = image_loader(Path(noisy_path))
        _check_image(noisy, "noisy")
        report["inputs"]["noisy"]["decoded_content_hash"] = canonical_arrays_hash({"image": noisy})
        report["inputs"]["noisy"]["recomputed_trainer_inputs"] = verify_trainer_inputs(
            noisy, prefix, arms, invariance)
    except ArtifactProblem as p:
        problems.append(p)
        return finish()
    except Exception as exc:
        problems.append(ArtifactProblem(INCONCLUSIVE, "noisy", f"measurement failure: {exc!r}"))
        return finish()

    # --- Stage 3: evaluator-only clean truth. ---
    try:
        if not Path(clean_path).is_file():
            raise ArtifactProblem(INCONCLUSIVE, "clean", "missing clean truth")
        report["clean_truth_read"] = True
        actual = sha256_file(Path(clean_path))
        report["inputs"]["clean"]["sha256"] = actual
        if actual != expected_clean_sha:
            raise ArtifactProblem(INCONCLUSIVE, "clean", "hash mismatch")
        clean = image_loader(Path(clean_path))
        _check_image(clean, "clean")
        report["inputs"]["clean"]["decoded_content_hash"] = canonical_arrays_hash({"image": clean})
        metrics = {a: arm_metrics(arms[a]["render"], noisy, clean) for a in ARMS}
    except ArtifactProblem as p:
        problems.append(p)
        return finish()
    except Exception as exc:
        problems.append(ArtifactProblem(INCONCLUSIVE, "measurement", repr(exc)))
        return finish()
    report["metrics"] = metrics
    for a in ARMS:
        for k in ("noisy_C_mse", "clean_C_mse"):
            if not math.isfinite(metrics[a][k]):
                problems.append(ArtifactProblem(INCONCLUSIVE, a, f"non-finite {k}"))
    if problems:
        return finish()

    crit = {key: _criterion(metrics["control_r1"][key], metrics["control_r2"][key],
                            metrics["holdout"][key])
            for key in ("noisy_C_mse", "clean_C_mse")}
    report["criteria"] = crit
    return finish("preliminary_pass" if all(c["passes"] for c in crit.values()) else "no_go")


# ---------------------------------------------------------------------------
# CLI (finding 8)
# ---------------------------------------------------------------------------
def _write_json_atomic(out: Path, payload: Dict) -> None:
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    with tmp.open("x", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fixed P1817 holdout-birth evaluator. Exit 0 = preliminary_pass, "
                    "10 = no_go, 20 = inconclusive, 30 = invalid, 40 = output refused "
                    "(nothing evaluated), 50 = evaluator error.")
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--noisy", type=Path, required=True)
    ap.add_argument("--clean", type=Path, required=True, help="evaluator-only clean truth")
    ap.add_argument("--out", type=Path, required=True, help="new JSON report path")
    args = ap.parse_args(argv)
    out: Path = args.out

    # Reserve the output before any artifact or image is opened.
    try:
        with out.open("x", encoding="utf-8") as fh:
            json.dump(RESERVATION_RECORD, fh)
            fh.write("\n")
    except OSError as exc:
        print(json.dumps({"error": f"cannot reserve report path; nothing evaluated: {exc!r}",
                          "report": str(out), "exit_code": EXIT_OUTPUT_REFUSED}), file=sys.stderr)
        return EXIT_OUTPUT_REFUSED

    try:
        report = evaluate(args.run_root, args.noisy, args.clean)
        decision = report.get("decision")
        code = EXIT_CODES.get(decision, EXIT_EVALUATOR_ERROR)
        if code == EXIT_EVALUATOR_ERROR:
            report["decision"] = INCONCLUSIVE
            report["evaluator_error"] = f"unknown decision {decision!r}"
    except Exception as exc:
        report = {"classification": "auxiliary/development evaluator output; not an independent test",
                  "decision": INCONCLUSIVE, "evaluator_error": repr(exc)}
        code = EXIT_EVALUATOR_ERROR
    report["report_status"] = "final"
    report["exit_code"] = code
    try:
        _write_json_atomic(out, report)
    except Exception as exc:
        print(json.dumps({"error": f"report finalization failed: {exc!r}", "report": str(out),
                          "exit_code": EXIT_EVALUATOR_ERROR}), file=sys.stderr)
        return EXIT_EVALUATOR_ERROR
    print(json.dumps({"decision": report["decision"], "exit_code": code, "report": str(out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
