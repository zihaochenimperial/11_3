#!/usr/bin/env python3
"""P1817 matched local holdout-birth pilot (contract 2026-11-04, amended 2026-11-05).

STATUS: NO LAUNCH. ``main`` raises before any execution path. This file is a
draft implementation of the amended design and has not been independently
audited or GPU-smoked. Nothing it contains is a result.

Amended design (research/P1817_PILOT_AMENDMENT_20261105.md):

  prefix     : steps 1..500 once, A-fold loss only; then build the A-derived
               256-candidate pool. Save parameters, pool and RNG states (before
               and after pool construction) with hashes. No candidate is chosen.
  continue   : fork one arm from the saved prefix + pool. Arms are exactly
               control_r1, control_r2 (first 64) and holdout (top 64 by noisy
               B-fold squared-error reduction inside the candidate's 16x16
               tile). Adam is re-created at birth, as in pinned upstream
               ``model.py`` ``_add_gaussians``. Steps 501..1000 use A only.
  invariance : from the saved prefix, (a) CPU equality of A/B-derived inputs
               under a C-only perturbation, (b) forward-only stability check,
               then recompute pool, scores and selection under both C inputs
               and require exact equality.

The trainer never holds C values (NaN sentinel) and never reads clean truth.
The fixed evaluator ``scripts/analyze_p1817_holdout_birth.py`` reads the
finalized artifacts written here. Artifact format: see ``ARTIFACT_FORMAT``.
Each run directory holds ``.npz`` array files (no pickle) and a
``manifest.json`` written last via atomic rename; a run is finalized only when
its manifest has ``status == "completed"``. On any exception a manifest with
``status == "failed"`` is written instead.
"""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

# -----------------------------------------------------------------------------
# Pin upstream Image-GS on the import path.
# -----------------------------------------------------------------------------
WSL_UPSTREAM = Path("/home/research/msc_inverse_research/src/image-gs")
UPSTREAM_ROOT = (
    WSL_UPSTREAM if WSL_UPSTREAM.is_dir()
    else Path(__file__).resolve().parent.parent / "upstream" / "image-gs"
)
sys.path.insert(0, str(UPSTREAM_ROOT))
sys.path.insert(0, str(UPSTREAM_ROOT / "gsplat"))

_original_cwd = Path.cwd()
try:
    # Upstream resolves its bundled font against cwd while importing.
    os.chdir(UPSTREAM_ROOT)
    from model import GaussianSplatting2D  # noqa: E402
    from utils.image_utils import load_images  # noqa: E402
    from utils.misc_utils import save_cfg  # noqa: E402
    from gsplat import project_gaussians_2d_scale_rot, rasterize_gaussians_sum  # noqa: E402
finally:
    os.chdir(_original_cwd)
from p1817_fold_boundary import (  # noqa: E402
    fold_flat_indices,
    hash_ab_values,
    perturb_c_only,
    split_ab_values,
    validate_proposal_indices,
)

# -----------------------------------------------------------------------------
# Frozen contract constants.
# -----------------------------------------------------------------------------
EXPECTED_INPUT_SHA256 = (
    "af17835d24f94488fa042efbfda00aa21628b5c0f299835404c75e7e359b0632"
)
EXPECTED_UPSTREAM_COMMIT = "03088368d42684fb54225c981cfd94b58cc0393a"
EXPECTED_UPSTREAM_LICENSE = "MIT"
DEFAULT_HEAVY_ROOT = Path(
    "/home/research/msc_inverse_research/runs/p1817_holdout_birth_20261104"
)

PILOT_SEED = 123
PILOT_MAX_STEPS = 1000
PILOT_BIRTH_STEP = 500
PILOT_INITIAL_GAUSSIANS = 256
PILOT_FINAL_GAUSSIANS = 320
PILOT_BIRTH_COUNT = 64
PILOT_CANDIDATE_POOL = 256
PILOT_IMG_H = PILOT_IMG_W = 192

PILOT_INIT_SCALE = 5.0
PILOT_POS_LR = 5.0e-4
PILOT_SCALE_LR = 2.0e-3
PILOT_ROT_LR = 2.0e-3
PILOT_FEAT_LR = 5.0e-3

# -----------------------------------------------------------------------------
# Frozen artifact format (must match scripts/analyze_p1817_holdout_birth.py).
# -----------------------------------------------------------------------------
ARTIFACT_FORMAT = "p1817-holdout-birth-artifact-v2"
_ARRAY_HASH_DOMAIN = b"P1817-holdout-birth-arrays-v2"
PREFIX_DIRNAME = "prefix"
INVARIANCE_DIRNAME = "invariance"
ARM_ROLES = {"control_r1": "control", "control_r2": "control", "holdout": "holdout"}
PARAM_KEYS = ("xy", "scale", "rot", "feat", "vis_feat")
LOCK_NAME = ".p1817_single_runner.lock"


# -----------------------------------------------------------------------------
# Hash / audit helpers.
# -----------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_tensor(t: torch.Tensor) -> str:
    arr = t.detach().cpu().contiguous().to(torch.float32).numpy()
    return hashlib.sha256(arr.tobytes()).hexdigest()


def canonical_arrays_hash(arrays: Dict[str, np.ndarray]) -> str:
    """Domain-separated SHA-256 over sorted keys, dtype, shape and bytes."""
    h = hashlib.sha256()
    h.update(_ARRAY_HASH_DOMAIN)
    for key in sorted(arrays):
        arr = np.ascontiguousarray(np.asarray(arrays[key]))
        h.update(f"|{key}:{arr.dtype.str}:{tuple(arr.shape)}|".encode("ascii"))
        h.update(arr.tobytes())
    return h.hexdigest()


def _write_npz(run_dir: Path, name: str, arrays: Dict[str, np.ndarray]) -> Dict:
    fname = f"{name}.npz"
    path = run_dir / fname
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    clean = {k: np.ascontiguousarray(np.asarray(v)) for k, v in arrays.items()}
    np.savez(path, **clean)
    return {
        "file": fname,
        "sha256": _sha256_file(path),
        "content_hash": canonical_arrays_hash(clean),
    }


def _read_npz_verified(run_dir: Path, entry: Dict) -> Dict[str, np.ndarray]:
    path = run_dir / entry["file"]
    if _sha256_file(path) != entry["sha256"]:
        raise RuntimeError(f"File hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as data:
        arrays = {k: data[k].copy() for k in data.files}
    if canonical_arrays_hash(arrays) != entry["content_hash"]:
        raise RuntimeError(f"Content hash mismatch: {path}")
    return arrays


def _write_manifest(run_dir: Path, manifest: Dict) -> Path:
    path = run_dir / "manifest.json"
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    tmp = run_dir / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def _reserve_run_dir(path: Path) -> Path:
    """Atomically reserve a fresh run directory; never reuse or clean one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(exist_ok=False)
    return path


@contextlib.contextmanager
def _single_runner_lock(run_root: Path):
    run_root.mkdir(parents=True, exist_ok=True)
    lock = run_root / LOCK_NAME
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"pid={os.getpid()} host={platform.node()}\n".encode())
        os.close(fd)
        yield
    finally:
        lock.unlink()


def _sync(device: str) -> None:
    if torch.cuda.is_available() and "cuda" in device:
        torch.cuda.synchronize(device)


def _verify_upstream_source() -> Path:
    """Refuse dirty upstream source or a mismatched commit."""
    if not (UPSTREAM_ROOT / ".git").is_dir():
        raise RuntimeError(f"Upstream {UPSTREAM_ROOT} is not a git repository.")

    def _git(*cmd: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(UPSTREAM_ROOT), *cmd], text=True
        ).strip()

    commit = _git("log", "-1", "--format=%H")
    if commit != EXPECTED_UPSTREAM_COMMIT:
        raise RuntimeError(
            f"Upstream commit mismatch: found {commit}, expected "
            f"{EXPECTED_UPSTREAM_COMMIT}. Pin upstream before running this pilot."
        )
    dirty = _git("status", "--porcelain")
    if dirty:
        raise RuntimeError(f"Upstream source tree is dirty; refusing to run.\n{dirty}")
    return UPSTREAM_ROOT


def _verify_input_image(input_path: Path) -> None:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")
    digest = _sha256_file(input_path)
    if digest != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"Input SHA-256 mismatch for {input_path}: got {digest}, expected "
            f"{EXPECTED_INPUT_SHA256}."
        )


# -----------------------------------------------------------------------------
# RNG state capture / restore (numpy, python, torch CPU, CUDA).
# -----------------------------------------------------------------------------
def capture_rng_state() -> Dict[str, np.ndarray]:
    st = np.random.get_state()
    if st[0] != "MT19937":
        raise RuntimeError(f"Unexpected numpy RNG {st[0]}")
    py = random.getstate()
    out = {
        "np_keys": np.asarray(st[1], dtype=np.uint32),
        "np_pos": np.asarray(st[2], dtype=np.int64),
        "np_has_gauss": np.asarray(st[3], dtype=np.int64),
        "np_cached_gaussian": np.asarray(st[4], dtype=np.float64),
        "py_version": np.asarray(py[0], dtype=np.int64),
        "py_internal": np.asarray(py[1], dtype=np.int64),
        "py_gauss_is_none": np.asarray(py[2] is None),
        "py_gauss_next": np.asarray(0.0 if py[2] is None else py[2], dtype=np.float64),
        "torch_cpu": torch.get_rng_state().numpy().copy(),
    }
    cuda_states = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []
    out["cuda_count"] = np.asarray(len(cuda_states), dtype=np.int64)
    for i, s in enumerate(cuda_states):
        out[f"cuda_{i}"] = s.numpy().copy()
    return out


def restore_rng_state(state: Dict[str, np.ndarray]) -> None:
    np.random.set_state((
        "MT19937",
        state["np_keys"].astype(np.uint32),
        int(state["np_pos"]),
        int(state["np_has_gauss"]),
        float(state["np_cached_gaussian"]),
    ))
    gauss = None if bool(state["py_gauss_is_none"]) else float(state["py_gauss_next"])
    random.setstate((
        int(state["py_version"]),
        tuple(int(v) for v in state["py_internal"]),
        gauss,
    ))
    torch.set_rng_state(torch.from_numpy(state["torch_cpu"].astype(np.uint8)))
    n = int(state["cuda_count"])
    have = torch.cuda.device_count() if torch.cuda.is_available() else 0
    if n != have:
        raise RuntimeError(f"Saved RNG has {n} CUDA states; this process has {have}.")
    if n:
        torch.cuda.set_rng_state_all(
            [torch.from_numpy(state[f"cuda_{i}"].astype(np.uint8)) for i in range(n)]
        )


# -----------------------------------------------------------------------------
# Argument assembly.
# -----------------------------------------------------------------------------
def _build_base_args(
    variant: str,
    input_path: Path,
    device: str,
    log_dir: Path,
    seed: int,
) -> argparse.Namespace:
    """Return a Namespace that satisfies GaussianSplatting2D.__init__.

    The configuration is frozen by the pilot contract.
    """
    args = argparse.Namespace()

    # Core
    args.seed = seed
    args.device = device
    args.eval = False
    args.render_height = 2048

    # Bit precision (quantization disabled -> full float storage)
    args.quantize = False
    args.pos_bits = 32
    args.scale_bits = 32
    args.rot_bits = 32
    args.feat_bits = 32

    # Logging
    args.log_dir = str(log_dir)
    args.log_level = "INFO"
    args.save_image_format = "png"
    args.save_plot_format = "png"
    args.vis_gaussians = False
    args.save_image_steps = 100_000
    args.save_ckpt_steps = 100_000
    args.eval_steps = 100

    # Target image
    args.gamma = 1.0
    args.data_root = str(input_path.parent)
    args.input_path = input_path.name
    args.downsample = False
    args.downsample_ratio = 2.0

    # Gaussians: progressive birth from 256 to 320 at step 500.
    args.num_gaussians = PILOT_FINAL_GAUSSIANS
    args.init_scale = PILOT_INIT_SCALE
    args.topk = 10
    args.disable_topk_norm = False
    args.disable_inverse_scale = False
    args.ckpt_file = ""
    args.disable_color_init = True  # features must be random, not target-derived
    args.init_mode = "random"       # positions random, not gradient/saliency
    args.init_random_ratio = 1.0
    args.smap_filter_size = 20

    # Loss: masked L2 on A only; L1/SSIM explicitly disabled.
    args.l1_loss_ratio = 0.0
    args.l2_loss_ratio = 1.0
    args.ssim_loss_ratio = 0.0

    # Optimization
    args.disable_tiles = False
    args.max_steps = PILOT_MAX_STEPS
    args.pos_lr = PILOT_POS_LR
    args.scale_lr = PILOT_SCALE_LR
    args.rot_lr = PILOT_ROT_LR
    args.feat_lr = PILOT_FEAT_LR
    args.disable_lr_schedule = True
    args.decay_ratio = 10.0
    args.check_decay_steps = 1000
    args.max_decay_times = 1
    args.decay_threshold = 1e-3

    # Progressive optimization: one fixed birth at step 500.
    args.disable_prog_optim = False
    args.initial_ratio = PILOT_INITIAL_GAUSSIANS / PILOT_FINAL_GAUSSIANS
    args.add_steps = PILOT_BIRTH_STEP
    args.add_times = 1
    args.post_min_steps = PILOT_MAX_STEPS - PILOT_BIRTH_STEP

    # Pilot bookkeeping (not consumed by upstream)
    args.pilot_variant = variant
    return args


# -----------------------------------------------------------------------------
# Subclass: enforce the holdout-birth contract inside Image-GS.
# -----------------------------------------------------------------------------
class P1817HoldoutBirthPilot(GaussianSplatting2D):
    """Upstream-read-only subclass implementing the P1817 pilot contract.

    Training is driven by ``train_steps`` (a copy of the core of upstream
    ``optimize``); upstream ``optimize``/``_add_gaussians`` are never used.
    """

    def __init__(
        self,
        args: argparse.Namespace,
        variant: str,
        perturb_c: bool = False,
    ):
        self.pilot_variant = variant
        self.perturb_c = perturb_c
        super().__init__(args)
        # After __init__, upstream has created 256 initial Gaussians.
        if self.num_gaussians != PILOT_INITIAL_GAUSSIANS:
            raise RuntimeError(
                f"Contract violation: expected {PILOT_INITIAL_GAUSSIANS} initial "
                f"Gaussians, got {self.num_gaussians}."
            )
        if self.total_num_gaussians != PILOT_FINAL_GAUSSIANS:
            raise RuntimeError(
                f"Contract violation: expected total {PILOT_FINAL_GAUSSIANS} "
                f"Gaussians, got {self.total_num_gaussians}."
            )
        if self.disable_tiles or self.quantize or self.disable_inverse_scale:
            raise RuntimeError("Pilot requires tiled, unquantized, inverse-scale model")
        self.step = 0

    # -------------------------------------------------------------------------
    # Logging: never rmtree; the run directory must be fresh.
    # -------------------------------------------------------------------------
    def _init_logging(self, args):
        if self.evaluate:
            raise RuntimeError("Pilot does not use upstream eval mode")
        self.log_dir = args.log_dir
        self.log_level = args.log_level
        self.ckpt_dir = os.path.join(self.log_dir, "checkpoints")
        self.train_dir = os.path.join(self.log_dir, "train")
        self.eval_dir = os.path.join(self.log_dir, "eval")
        self.save_image_format = args.save_image_format
        self.save_plot_format = args.save_plot_format
        self.vis_gaussians = args.vis_gaussians
        self.save_image_steps = args.save_image_steps
        self.save_ckpt_steps = args.save_ckpt_steps
        self.eval_steps = args.eval_steps
        os.makedirs(self.log_dir, exist_ok=False)
        os.makedirs(self.ckpt_dir, exist_ok=False)
        os.makedirs(self.train_dir, exist_ok=False)
        self._gen_logger(args)
        save_cfg(path=f"{self.log_dir}/cfg_train.yaml", args=args)

    # -------------------------------------------------------------------------
    # Target loading + fold mask + optional C perturbation.
    # -------------------------------------------------------------------------
    def _init_target(self, args):
        """Load target without the upstream full-target logging path."""
        if args.downsample:
            raise ValueError("Pilot does not permit downsampling")
        if args.gamma != 1.0:
            raise ValueError("Pilot requires gamma == 1.0")
        self.gamma = args.gamma
        self.downsample = False
        self.block_h, self.block_w = 16, 16
        self._load_target_images(str(Path(args.data_root) / args.input_path))
        self.num_pixels = self.img_h * self.img_w

    def _load_target_images(self, path, downsample_ratio=None):
        """Load the verified noisy image and attach the A/B/C fold mask."""
        gt_images, input_channels, image_fnames, bit_depths = load_images(
            load_path=path, downsample_ratio=downsample_ratio, gamma=self.gamma
        )
        if self.perturb_c:
            gt_images = perturb_c_only(gt_images)
        ab = split_ab_values(gt_images)
        # Hash of every A/B-derived trainer input (invariance layer a).
        self.ab_hash = hash_ab_values(ab)
        # Do not retain a reference to the original target or any C values.
        safe = np.full(gt_images.shape, np.nan, dtype=np.float32)
        safe_flat = safe.reshape(safe.shape[0], -1)
        safe_flat[:, ab.a_index] = ab.a_values
        safe_flat[:, ab.b_index] = ab.b_values
        del gt_images, safe_flat, ab
        self.gt_images = torch.from_numpy(safe).to(dtype=self.dtype, device=self.device)
        self.input_channels = input_channels
        self.image_fnames = image_fnames
        self.bit_depths = bit_depths
        self.img_h, self.img_w = self.gt_images.shape[1:]
        self.tile_bounds = (
            (self.img_w + self.block_w - 1) // self.block_w,
            (self.img_h + self.block_h - 1) // self.block_h,
            1,
        )
        if (self.img_h, self.img_w) != (PILOT_IMG_H, PILOT_IMG_W):
            raise ValueError(
                f"Contract violation: expected 192x192 input, got "
                f"{self.img_h}x{self.img_w}."
            )
        self._build_fold_mask()

    def _build_fold_mask(self):
        """Deterministic (x + 2*y) % 3 checkerboard. A=0, B=1, C=2."""
        h = torch.arange(self.img_h, dtype=torch.long, device=self.device)
        w = torch.arange(self.img_w, dtype=torch.long, device=self.device)
        # fold[y, x] = (x + 2*y) % 3
        fold = (w[None, :] + 2 * h[:, None]) % 3
        self.fold_mask = fold
        self.a_mask_bool = fold == 0
        self.b_mask_bool = fold == 1
        self.c_mask_bool = fold == 2
        self.fold_counts = {
            "A": int(self.a_mask_bool.sum().item()),
            "B": int(self.b_mask_bool.sum().item()),
            "C": int(self.c_mask_bool.sum().item()),
        }
        self.fold_indices = fold_flat_indices(self.img_h, self.img_w)

    def trainer_target_hash(self) -> str:
        """Hash of the trainer-held target tensor (C is a NaN sentinel)."""
        return _sha256_tensor(self.gt_images)

    # -------------------------------------------------------------------------
    # Loss: masked L2 on A only; L1/SSIM forbidden.
    # -------------------------------------------------------------------------
    def _init_loss(self, args):
        super()._init_loss(args)
        if args.l1_loss_ratio > 1e-7 or args.ssim_loss_ratio > 1e-7:
            raise ValueError(
                "Pilot contract forbids L1/SSIM loss ratios. Set both to 0.0."
            )

    def _get_total_loss(self, images):
        """L2 on A-fold pixels only."""
        diff_a = images[:, self.a_mask_bool] - self.gt_images[:, self.a_mask_bool]
        se_a = diff_a ** 2
        self.l2_loss = self.l2_loss_ratio * se_a.mean()
        self.total_loss = self.l2_loss
        self.l1_loss = None
        self.ssim_loss = None

    # -------------------------------------------------------------------------
    # Evaluation: A-only metrics; extra metrics (LPIPS/FLIP/MS-SSIM) disabled.
    # -------------------------------------------------------------------------
    def _evaluate(self, log=True, upsample=False):
        if upsample:
            log = False
        images = torch.pow(
            torch.clamp(self._render_images(upsample=upsample), 0.0, 1.0),
            1.0 / self.gamma,
        )
        gt_images = torch.pow(
            self.gt_images_upsampled if upsample else self.gt_images,
            1.0 / self.gamma,
        )
        a_mask = self.a_mask_bool
        mse = ((images[:, a_mask] - gt_images[:, a_mask]) ** 2).mean()
        if mse.item() <= 1e-7:
            psnr = float("inf")
        else:
            psnr = (20.0 * torch.log10(1.0 / torch.sqrt(mse))).item()
        ssim = 0.0
        if log:
            self.psnr_curr, self.ssim_curr = psnr, ssim
            loss_results = f"Loss: {self.total_loss.item():.4f}"
            loss_results += (
                f", L2: {self.l2_loss.item():.4f}"
                if self.l2_loss is not None
                else ""
            )
            time_results = (
                f"Total: {self.total_time_accum:.2f} s | "
                f"Render: {self.render_time_accum:.2f} s"
            )
            self.worklog.info(
                f"Step: {self.step:d} | {time_results} | {loss_results} | "
                f"PSNR(A): {self.psnr_curr:.2f}"
            )
        return psnr, ssim

    def _evaluate_extra(self):
        """Do not run LPIPS/FLIP/MS-SSIM inside the pilot."""
        self.lpips_final = 0.0
        self.flip_final = 0.0
        self.msssim_final = 0.0

    def optimize(self):
        raise RuntimeError("Use train_steps; upstream optimize is not used")

    def _add_gaussians(self, add_num, plot_gaussians=False):
        # Upstream birth blurs the full target (fold mixing). Never used.
        raise RuntimeError("Upstream _add_gaussians is forbidden in this pilot")

    # -------------------------------------------------------------------------
    # Training loop (core of upstream optimize, model.py:408-419).
    # -------------------------------------------------------------------------
    def reset_accumulators(self):
        self.psnr_curr, self.ssim_curr = 0.0, 0.0
        self.render_time_accum, self.total_time_accum = 0.0, 0.0

    def train_steps(self, first: int, last: int) -> None:
        if self.optimizer is None:
            raise RuntimeError("Optimizer missing; birth must re-create Adam first")
        for step in range(first, last + 1):
            self.step = step
            self.optimizer.zero_grad()
            images, render_time = self.forward(self.img_h, self.img_w, self.tile_bounds)
            self.render_time_accum += render_time
            begin = time.perf_counter()
            self._get_total_loss(images)
            if not bool(torch.isfinite(self.total_loss).item()):
                raise RuntimeError(f"Non-finite A loss at step {step}")
            self.total_loss.backward()
            self.optimizer.step()
            self.total_time_accum += time.perf_counter() - begin + render_time
            with torch.no_grad():
                if step % self.eval_steps == 0:
                    self._evaluate(log=True, upsample=False)

    # -------------------------------------------------------------------------
    # Parameter snapshot / restore.
    # -------------------------------------------------------------------------
    def param_arrays(self) -> Dict[str, np.ndarray]:
        return {
            k: getattr(self, k).detach().cpu().contiguous().to(torch.float32).numpy().copy()
            for k in PARAM_KEYS
        }

    def load_param_arrays(self, arrays: Dict[str, np.ndarray], n: int) -> None:
        for k in PARAM_KEYS:
            arr = arrays[k]
            if arr.shape[0] != n or arr.dtype != np.float32 or not np.isfinite(arr).all():
                raise RuntimeError(f"Bad saved parameter {k}: {arr.shape} {arr.dtype}")
            t = torch.from_numpy(arr.copy()).to(dtype=self.dtype, device=self.device)
            setattr(self, k, nn.Parameter(t, requires_grad=(k != "vis_feat")))
        self.num_gaussians = n
        # The __init__ optimizer refers to discarded tensors; birth re-creates Adam.
        self.optimizer = None

    # -------------------------------------------------------------------------
    # Shared A-derived candidate pool (built once, in the prefix).
    # -------------------------------------------------------------------------
    def build_candidate_pool(self) -> Dict[str, np.ndarray]:
        if self.step != PILOT_BIRTH_STEP:
            raise RuntimeError(f"Pool must be built at step {PILOT_BIRTH_STEP}, got {self.step}.")
        if self.num_gaussians != PILOT_INITIAL_GAUSSIANS:
            raise RuntimeError(f"Expected {PILOT_INITIAL_GAUSSIANS} Gaussians before birth.")
        with torch.no_grad():
            raw_images = self._render_images(upsample=False)
            images = torch.pow(torch.clamp(raw_images, 0.0, 1.0), 1.0 / self.gamma)
            diff_a = self.gt_images[:, self.a_mask_bool] - images[:, self.a_mask_bool]
            if not bool(torch.isfinite(diff_a).all().item()):
                raise RuntimeError("Non-finite A residual at pool construction")

            a_flat = self.fold_indices["A"]
            prob = (diff_a ** 2).mean(dim=0).cpu().numpy().astype(np.float64)
            s = prob.sum()
            if not np.isfinite(s):
                raise RuntimeError("Non-finite A residual mass")
            if s <= 0.0:
                prob = np.ones(len(a_flat), dtype=np.float64) / len(a_flat)
            else:
                prob = prob / s
            prob = prob / prob.sum()  # guard against residual fp drift
            selected = np.random.choice(
                a_flat, size=PILOT_CANDIDATE_POOL, replace=False, p=prob
            ).astype(np.int64)
            validate_proposal_indices(
                selected, self.img_h, self.img_w, expected_count=PILOT_CANDIDATE_POOL
            )

            sel_t = torch.from_numpy(selected).to(self.device)
            new_xy = self.pixel_xy[sel_t].detach().clone()
            new_scale = torch.full(
                (PILOT_CANDIDATE_POOL, 2), 1.0 / self.init_scale,
                dtype=self.dtype, device=self.device,
            )
            new_rot = torch.zeros(PILOT_CANDIDATE_POOL, 1, dtype=self.dtype, device=self.device)
            a_positions = np.searchsorted(a_flat, selected)
            if not np.array_equal(a_flat[a_positions], selected):
                raise RuntimeError("Pool index not found in A fold")
            pos_t = torch.from_numpy(a_positions.astype(np.int64)).to(self.device)
            new_feat = diff_a[:, pos_t].transpose(0, 1).contiguous()
            new_vis_feat = torch.rand_like(new_feat)

        pool = {"indices": selected}
        for k, t in (("xy", new_xy), ("scale", new_scale), ("rot", new_rot),
                     ("feat", new_feat), ("vis_feat", new_vis_feat)):
            pool[k] = t.detach().cpu().contiguous().to(torch.float32).numpy().copy()
            if not np.isfinite(pool[k]).all():
                raise RuntimeError(f"Non-finite candidate {k}")
        return pool

    def _pool_tensors(self, pool: Dict[str, np.ndarray]) -> Dict[str, torch.Tensor]:
        return {
            k: torch.from_numpy(pool[k].copy()).to(dtype=self.dtype, device=self.device)
            for k in PARAM_KEYS
        }

    # -------------------------------------------------------------------------
    # Selection (from the saved pool) and birth.
    # -------------------------------------------------------------------------
    def select_candidates(
        self, role: str, pool: Dict[str, np.ndarray]
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if role == "control":
            return np.arange(PILOT_BIRTH_COUNT, dtype=np.int64), None
        if role != "holdout":
            raise ValueError(f"Unknown role: {role}")
        pt = self._pool_tensors(pool)
        scores = self._score_candidates_by_b_tile(pt["xy"], pt["scale"], pt["rot"], pt["feat"])
        if scores.shape != (PILOT_CANDIDATE_POOL,) or not np.isfinite(scores).all():
            raise RuntimeError("Non-finite holdout candidate score")
        chosen = np.argsort(-scores, kind="stable")[:PILOT_BIRTH_COUNT].astype(np.int64)
        return chosen, scores

    def birth_from_pool(self, pool: Dict[str, np.ndarray], chosen: np.ndarray) -> None:
        if self.step != PILOT_BIRTH_STEP:
            raise RuntimeError(f"Birth must occur at step {PILOT_BIRTH_STEP}, got {self.step}.")
        if self.num_gaussians != PILOT_INITIAL_GAUSSIANS:
            raise RuntimeError(f"Expected {PILOT_INITIAL_GAUSSIANS} Gaussians before birth.")
        chosen = np.asarray(chosen, dtype=np.int64)
        if (chosen.shape != (PILOT_BIRTH_COUNT,) or np.unique(chosen).size != PILOT_BIRTH_COUNT
                or chosen.min() < 0 or chosen.max() >= PILOT_CANDIDATE_POOL):
            raise RuntimeError("Invalid chosen candidate indices")
        pt = self._pool_tensors(pool)
        idx = torch.from_numpy(chosen).to(self.device)
        with torch.no_grad():
            for k in PARAM_KEYS:
                old = getattr(self, k).detach().clone()
                new = torch.cat([old, pt[k][idx]], dim=0)
                setattr(self, k, nn.Parameter(new, requires_grad=(k != "vis_feat")))
        self.num_gaussians += PILOT_BIRTH_COUNT
        if self.num_gaussians != PILOT_FINAL_GAUSSIANS:
            raise RuntimeError("Final Gaussian count mismatch after birth")
        # Re-create Adam exactly as pinned upstream model.py:597-600.
        self.optimizer = torch.optim.Adam(
            [
                {"params": self.xy, "lr": self.pos_lr},
                {"params": self.scale, "lr": self.scale_lr},
                {"params": self.rot, "lr": self.rot_lr},
                {"params": self.feat, "lr": self.feat_lr},
            ]
        )
        self.worklog.info(
            f"Step: {self.step:d} | Adding {PILOT_BIRTH_COUNT:d} Gaussians "
            f"({PILOT_INITIAL_GAUSSIANS:d} -> {self.num_gaussians:d})"
        )

    def _render_with_candidate(
        self,
        xy: torch.Tensor,
        scale: torch.Tensor,
        rot: torch.Tensor,
        feat: torch.Tensor,
    ) -> torch.Tensor:
        """Render augmented tensors without replacing registered parameters."""
        with torch.no_grad():
            if self.disable_tiles or self.quantize:
                raise RuntimeError("Pilot requires tiled, unquantized rendering")
            all_xy = torch.cat([self.xy, xy], dim=0)
            all_scale = torch.cat([self.scale, scale], dim=0)
            all_rot = torch.cat([self.rot, rot], dim=0)
            all_feat = torch.cat([self.feat, feat], dim=0)
            if not self.disable_inverse_scale:
                all_scale = 1.0 / all_scale
            projected = project_gaussians_2d_scale_rot(
                all_xy, all_scale, all_rot, self.img_h, self.img_w, self.tile_bounds
            )
            projected_xy, radii, conics, num_tiles_hit = projected
            image = rasterize_gaussians_sum(
                projected_xy, radii, conics, num_tiles_hit, all_feat,
                self.img_h, self.img_w, self.block_h, self.block_w,
                not self.disable_topk_norm,
            )
            return image.view(-1, self.img_h, self.img_w, self.feat_dim).permute(
                0, 3, 1, 2
            ).contiguous().squeeze(0)

    def _score_candidates_by_b_tile(
        self,
        cand_xy: torch.Tensor,
        cand_scale: torch.Tensor,
        cand_rot: torch.Tensor,
        cand_feat: torch.Tensor,
    ) -> np.ndarray:
        """Per-candidate B-fold squared-error reduction inside its 16x16 tile."""
        with torch.no_grad():
            current_raw = self._render_images(upsample=False)
            current = torch.pow(
                torch.clamp(current_raw, 0.0, 1.0), 1.0 / self.gamma
            )
            gt = torch.pow(self.gt_images, 1.0 / self.gamma)

            h, w = self.img_h, self.img_w
            n_tiles_x = (w + self.block_w - 1) // self.block_w
            n_tiles_y = (h + self.block_h - 1) // self.block_h

            # tile_ids[y, x] = linear tile index.
            tile_ids = torch.full(
                (h, w), -1, dtype=torch.long, device=self.device
            )
            for ty in range(n_tiles_y):
                y0 = ty * self.block_h
                y1 = min((ty + 1) * self.block_h, h)
                for tx in range(n_tiles_x):
                    x0 = tx * self.block_w
                    x1 = min((tx + 1) * self.block_w, w)
                    tile_ids[y0:y1, x0:x1] = ty * n_tiles_x + tx

            px = (cand_xy[:, 0] * w).long().clamp(0, w - 1)
            py = (cand_xy[:, 1] * h).long().clamp(0, h - 1)
            cand_tile = tile_ids[py, px].cpu().numpy()

            b_mask = self.b_mask_bool
            scores = np.empty(len(cand_xy), dtype=np.float64)
            current_cache: Dict[int, float] = {}

            for i in range(len(cand_xy)):
                tid = int(cand_tile[i])
                if tid not in current_cache:
                    tile_mask = tile_ids == tid
                    tile_b = tile_mask & b_mask
                    cnt = tile_b.sum().item()
                    if cnt == 0:
                        raise RuntimeError(
                            f"Tile {tid} contains no B-fold pixels; cannot "
                            f"compute holdout selection score."
                        )
                    current_cache[tid] = (
                        (current[:, tile_b] - gt[:, tile_b]) ** 2
                    ).mean().item()
                current_mse = current_cache[tid]

                extra_render = self._render_with_candidate(
                    cand_xy[i : i + 1],
                    cand_scale[i : i + 1],
                    cand_rot[i : i + 1],
                    cand_feat[i : i + 1],
                )
                extra = torch.pow(
                    torch.clamp(extra_render, 0.0, 1.0), 1.0 / self.gamma
                )
                tile_mask = tile_ids == tid
                tile_b = tile_mask & b_mask
                new_mse = ((extra[:, tile_b] - gt[:, tile_b]) ** 2).mean().item()
                if not (np.isfinite(current_mse) and np.isfinite(new_mse)):
                    raise RuntimeError(f"Non-finite B-tile MSE for candidate {i}")
                scores[i] = current_mse - new_mse
        return scores


# -----------------------------------------------------------------------------
# Run bookkeeping.
# -----------------------------------------------------------------------------
def _versions() -> Dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "hostname": platform.node(),
    }
    if torch.cuda.is_available():
        versions["cuda"] = torch.version.cuda or "unknown"
        try:
            versions["cuda_device_name"] = torch.cuda.get_device_name(
                torch.cuda.current_device()
            )
        except Exception:
            versions["cuda_device_name"] = "unknown"
    return versions


def _base_manifest(kind: str, device: str, input_path: Path) -> Dict:
    return {
        "artifact_format": ARTIFACT_FORMAT,
        "kind": kind,
        "classification": "auxiliary/development mechanism pilot",
        "seed": PILOT_SEED,
        "device": device,
        "input_path": str(input_path),
        "input_sha256": EXPECTED_INPUT_SHA256,
        "source_commit": EXPECTED_UPSTREAM_COMMIT,
        "source_license": EXPECTED_UPSTREAM_LICENSE,
        "upstream_path": str(UPSTREAM_ROOT),
        "pilot_script_sha256": _sha256_file(Path(__file__).resolve()),
        "versions": _versions(),
        "command": sys.argv,
        "fold_map": "(x + 2*y) % 3, A=0 fit/propose, B=1 select, C=2 audit",
        "initial_gaussians": PILOT_INITIAL_GAUSSIANS,
        "final_gaussians": PILOT_FINAL_GAUSSIANS,
        "birth_step": PILOT_BIRTH_STEP,
        "birth_count": PILOT_BIRTH_COUNT,
        "candidate_pool_size": PILOT_CANDIDATE_POOL,
        "max_steps": PILOT_MAX_STEPS,
        "started_unix": time.time(),
    }


def _peak_vram(device: str) -> int:
    if torch.cuda.is_available() and "cuda" in device:
        return int(torch.cuda.max_memory_allocated(device))
    return 0


def _reset_vram(device: str) -> None:
    if torch.cuda.is_available() and "cuda" in device:
        torch.cuda.reset_peak_memory_stats(device)


def _guarded(run_dir: Path, manifest: Dict, body) -> Dict:
    """Run body(); on any exception finalize a failed manifest and re-raise."""
    try:
        body(manifest)
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = repr(exc)
        manifest["traceback"] = traceback.format_exc()
        if not (run_dir / "manifest.json").exists():
            _write_manifest(run_dir, manifest)
        raise
    manifest["status"] = "completed"
    manifest["finished_unix"] = time.time()
    _write_manifest(run_dir, manifest)
    print(json.dumps({"status": "completed", "manifest": str(run_dir / "manifest.json")}))
    return manifest


def load_verified_prefix(run_root: Path) -> Dict:
    """Load the finalized prefix and verify every file and content hash."""
    run_dir = run_root / PREFIX_DIRNAME
    mpath = run_dir / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    if manifest.get("artifact_format") != ARTIFACT_FORMAT or manifest.get("kind") != "prefix":
        raise RuntimeError("Prefix manifest format/kind mismatch")
    if manifest.get("status") != "completed":
        raise RuntimeError(f"Prefix is not completed: {manifest.get('status')}")
    if manifest.get("input_sha256") != EXPECTED_INPUT_SHA256:
        raise RuntimeError("Prefix input hash mismatch")
    out = {"manifest": manifest, "manifest_sha256": _sha256_file(mpath)}
    for name in ("prefix_params", "candidate_pool", "rng_before_pool", "rng_after_pool"):
        out[name] = _read_npz_verified(run_dir, manifest["files"][name])
    validate_proposal_indices(
        out["candidate_pool"]["indices"], PILOT_IMG_H, PILOT_IMG_W,
        expected_count=PILOT_CANDIDATE_POOL,
    )
    out["ref"] = {
        "manifest_sha256": out["manifest_sha256"],
        "prefix_params_hash": manifest["files"]["prefix_params"]["content_hash"],
        "candidate_pool_hash": manifest["files"]["candidate_pool"]["content_hash"],
        "rng_before_pool_hash": manifest["files"]["rng_before_pool"]["content_hash"],
        "rng_after_pool_hash": manifest["files"]["rng_after_pool"]["content_hash"],
    }
    return out


# -----------------------------------------------------------------------------
# Commands.
# -----------------------------------------------------------------------------
def run_prefix(input_path: Path, device: str, run_root: Path) -> Dict:
    run_dir = _reserve_run_dir(run_root / PREFIX_DIRNAME)
    manifest = _base_manifest("prefix", device, input_path)

    def body(m: Dict) -> None:
        _reset_vram(device)
        _sync(device)
        t0 = time.perf_counter()
        args = _build_base_args("prefix", input_path, device, run_dir / "model", PILOT_SEED)
        model = P1817HoldoutBirthPilot(args, variant="prefix")
        model.reset_accumulators()
        _sync(device)
        t1 = time.perf_counter()
        model.train_steps(1, PILOT_BIRTH_STEP)
        _sync(device)
        t2 = time.perf_counter()
        rng_before = capture_rng_state()
        pool = model.build_candidate_pool()
        rng_after = capture_rng_state()
        params = model.param_arrays()
        _sync(device)
        t3 = time.perf_counter()
        m["files"] = {
            "prefix_params": _write_npz(run_dir, "prefix_params", params),
            "candidate_pool": _write_npz(run_dir, "candidate_pool", pool),
            "rng_before_pool": _write_npz(run_dir, "rng_before_pool", rng_before),
            "rng_after_pool": _write_npz(run_dir, "rng_after_pool", rng_after),
        }
        m.update({
            "steps_completed": PILOT_BIRTH_STEP,
            "fold_counts": model.fold_counts,
            "ab_hash": model.ab_hash,
            "trainer_target_hash": model.trainer_target_hash(),
            "timing_sec": {
                "init": t1 - t0, "train_1_500": t2 - t1, "pool": t3 - t2,
                "prefix_wall": t3 - t0,
            },
            "model_total_time_accum_sec": model.total_time_accum,
            "peak_vram_bytes": _peak_vram(device),
        })

    return _guarded(run_dir, manifest, body)


def run_arm(arm: str, input_path: Path, device: str, run_root: Path) -> Dict:
    if arm not in ARM_ROLES:
        raise ValueError(f"Unknown arm {arm}; expected one of {sorted(ARM_ROLES)}")
    role = ARM_ROLES[arm]
    prefix = load_verified_prefix(run_root)
    run_dir = _reserve_run_dir(run_root / arm)
    manifest = _base_manifest("arm", device, input_path)
    manifest.update({"arm": arm, "role": role, "prefix_ref": prefix["ref"]})

    def body(m: Dict) -> None:
        _reset_vram(device)
        _sync(device)
        t0 = time.perf_counter()
        args = _build_base_args(role, input_path, device, run_dir / "model", PILOT_SEED)
        model = P1817HoldoutBirthPilot(args, variant=role)
        if model.ab_hash != prefix["manifest"]["ab_hash"]:
            raise RuntimeError("A/B input hash differs from prefix")
        if model.trainer_target_hash() != prefix["manifest"]["trainer_target_hash"]:
            raise RuntimeError("Trainer target hash differs from prefix")
        model.load_param_arrays(prefix["prefix_params"], PILOT_INITIAL_GAUSSIANS)
        model.step = PILOT_BIRTH_STEP
        restore_rng_state(prefix["rng_after_pool"])
        _sync(device)
        t1 = time.perf_counter()
        chosen, scores = model.select_candidates(role, prefix["candidate_pool"])
        model.birth_from_pool(prefix["candidate_pool"], chosen)
        birth_params = model.param_arrays()
        _sync(device)
        t2 = time.perf_counter()
        model.reset_accumulators()
        model.train_steps(PILOT_BIRTH_STEP + 1, PILOT_MAX_STEPS)
        _sync(device)
        t3 = time.perf_counter()
        with torch.no_grad():
            render = model._render_images(upsample=False).detach().cpu().contiguous()
        final_params = {k: v for k, v in model.param_arrays().items()}
        _sync(device)
        t4 = time.perf_counter()
        m["files"] = {
            "selection": _write_npz(run_dir, "selection", {
                "selected": chosen,
                "scores": (np.zeros(0, dtype=np.float64) if scores is None
                           else scores.astype(np.float64)),
            }),
            "birth_params": _write_npz(run_dir, "birth_params", birth_params),
            "final_params": _write_npz(run_dir, "final_params", final_params),
            "final_render": _write_npz(run_dir, "final_render", {
                "render": render.to(torch.float32).numpy(),
            }),
        }
        m.update({
            "steps_completed": model.step,
            "num_gaussians_final": model.num_gaussians,
            "ab_hash": model.ab_hash,
            "trainer_target_hash": model.trainer_target_hash(),
            "timing_sec": {
                "setup": t1 - t0, "selection_and_birth": t2 - t1,
                "continuation_501_1000": t3 - t2, "finalize_render": t4 - t3,
                "arm_wall": t4 - t0,
            },
            "model_total_time_accum_sec": model.total_time_accum,
            "peak_vram_bytes": _peak_vram(device),
        })

    return _guarded(run_dir, manifest, body)


def run_invariance(input_path: Path, device: str, run_root: Path) -> Dict:
    prefix = load_verified_prefix(run_root)
    run_dir = _reserve_run_dir(run_root / INVARIANCE_DIRNAME)
    manifest = _base_manifest("invariance", device, input_path)
    manifest["prefix_ref"] = prefix["ref"]

    def body(m: Dict) -> None:
        _sync(device)
        t0 = time.perf_counter()
        checks: Dict[str, bool] = {}
        # (a) CPU exact equality of A/B-derived inputs under C-only perturbation.
        raw = load_images(load_path=str(input_path), gamma=1.0)[0]
        ab_normal = hash_ab_values(split_ab_values(raw))
        ab_perturbed = hash_ab_values(split_ab_values(perturb_c_only(raw)))
        del raw
        checks["cpu_ab_hash_equal_across_c"] = ab_normal == ab_perturbed
        checks["cpu_ab_hash_matches_prefix"] = ab_normal == prefix["manifest"]["ab_hash"]

        models = {}
        for tag, pc in (("normal", False), ("cperturb", True)):
            args = _build_base_args("invariance", input_path, device,
                                    run_dir / f"model_{tag}", PILOT_SEED)
            mdl = P1817HoldoutBirthPilot(args, variant="invariance", perturb_c=pc)
            mdl.load_param_arrays(prefix["prefix_params"], PILOT_INITIAL_GAUSSIANS)
            mdl.step = PILOT_BIRTH_STEP
            models[tag] = mdl
        n, p = models["normal"], models["cperturb"]
        checks["trainer_target_hash_equal_across_c"] = (
            n.trainer_target_hash() == p.trainer_target_hash()
            == prefix["manifest"]["trainer_target_hash"]
        )

        # (b0) Forward-only bitwise stability on this device.
        with torch.no_grad():
            r = [_sha256_tensor(mdl._render_images()) for mdl in (n, n, p, p)]
        checks["forward_repeat_bitwise_stable"] = r[0] == r[1] and r[2] == r[3]
        checks["forward_equal_across_models"] = r[0] == r[2]

        pool_saved = prefix["candidate_pool"]
        if checks["forward_repeat_bitwise_stable"]:
            # (b1) Recompute pool from the saved pre-pool RNG state.
            restore_rng_state(prefix["rng_before_pool"])
            pool_n = n.build_candidate_pool()
            restore_rng_state(prefix["rng_before_pool"])
            pool_p = p.build_candidate_pool()
            h_n, h_p = canonical_arrays_hash(pool_n), canonical_arrays_hash(pool_p)
            checks["pool_recompute_equal_across_c"] = h_n == h_p
            checks["pool_recompute_matches_saved"] = h_n == prefix["ref"]["candidate_pool_hash"]
            # (b2) Scores and selection on the saved pool under both C inputs.
            sel_n1, sc_n1 = n.select_candidates("holdout", pool_saved)
            sel_n2, sc_n2 = n.select_candidates("holdout", pool_saved)
            sel_p, sc_p = p.select_candidates("holdout", pool_saved)
            checks["scorer_repeat_bitwise_stable"] = (
                sc_n1.tobytes() == sc_n2.tobytes() and np.array_equal(sel_n1, sel_n2)
            )
            checks["scores_equal_across_c"] = sc_n1.tobytes() == sc_p.tobytes()
            checks["selection_equal_across_c"] = np.array_equal(sel_n1, sel_p)
            m["selected_normal"] = sel_n1.tolist()

        deterministic_leak = ("cpu_ab_hash_equal_across_c", "trainer_target_hash_equal_across_c")
        reproducibility = ("cpu_ab_hash_matches_prefix", "forward_repeat_bitwise_stable",
                           "forward_equal_across_models", "scorer_repeat_bitwise_stable",
                           "pool_recompute_matches_saved")
        leak_after_repro = ("pool_recompute_equal_across_c", "scores_equal_across_c",
                            "selection_equal_across_c")
        if not all(checks[k] for k in deterministic_leak):
            result = "failed_leakage"
        elif not all(checks.get(k, False) for k in reproducibility):
            result = "inconclusive"
        elif not all(checks.get(k, False) for k in leak_after_repro):
            result = "failed_leakage"
        else:
            result = "passed"
        _sync(device)
        m.update({
            "checks": checks,
            "invariance_result": result,
            "timing_sec": {"invariance_wall": time.perf_counter() - t0},
            "peak_vram_bytes": _peak_vram(device),
        })

    return _guarded(run_dir, manifest, body)


# -----------------------------------------------------------------------------
# CLI.
# -----------------------------------------------------------------------------
def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--input", type=Path, required=True, help="192x192 noisy PNG")
    p.add_argument("--device", default="cuda:0")
    p.add_argument(
        "--heavy-root",
        type=Path,
        default=DEFAULT_HEAVY_ROOT,
        help="Run root holding prefix/, control_r1/, control_r2/, holdout/, invariance/.",
    )
    return p


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P1817 holdout-birth pilot against pinned Image-GS (amended)."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    common = _common_parser()

    sub.add_parser("prefix", parents=[common], help="Shared steps 1-500 + A-derived pool.")
    cont = sub.add_parser("continue", parents=[common], help="Fork one arm from the prefix.")
    cont.add_argument("--arm", required=True, choices=sorted(ARM_ROLES))
    sub.add_parser("invariance", parents=[common],
                   help="C-only perturbation check from the saved prefix.")

    args = parser.parse_args()

    # The amended implementation and evaluator have not passed independent
    # review or the forward-reproducibility GPU smoke.  Keep all execution
    # paths closed; --help remains available.  Never remove without audit.
    raise RuntimeError(
        "NO LAUNCH: P1817 pilot repair and independent audit are incomplete. "
        "See research/P1817_PILOT_AMENDMENT_20261105.md."
    )

    # Fail-closed contract checks.
    _verify_upstream_source()
    _verify_input_image(args.input)

    run_root = args.heavy_root
    if not run_root.is_absolute():
        raise ValueError(
            f"--heavy-root must be an absolute path; got {run_root}. "
            f"Default is {DEFAULT_HEAVY_ROOT}."
        )

    with _single_runner_lock(run_root):
        if args.command == "prefix":
            run_prefix(args.input, args.device, run_root)
        elif args.command == "continue":
            run_arm(args.arm, args.input, args.device, run_root)
        elif args.command == "invariance":
            run_invariance(args.input, args.device, run_root)
        else:
            raise ValueError(args.command)


if __name__ == "__main__":
    main()
