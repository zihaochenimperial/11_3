"""Pure-CPU fold-boundary helpers for the P1817 holdout-birth pilot.

Status: preparation patch (infrastructure only). Nothing in this module is an
experimental result, and its existence does not make the GPU pilot launchable;
the NO LAUNCH preflight in
``runs/claude_research/p1817_opus_preflight_20261105/recovered-review.md``
still stands until the remaining repairs, amendment and independent audit are
done.

Scope (first safe patch, repair-order item 1 of the review):

* deterministic fold labels ``(x + 2*y) % 3`` with A=0 (fit/propose),
  B=1 (select), C=2 (audit), as frozen in
  ``research/P1817_HOLDOUT_BIRTH_PILOT_CONTRACT_20261104.md``;
* row-major flat indices ``y*W + x`` (matching upstream ``pixel_xy``), one
  disjoint sorted array per fold;
* gathering only A and B values from an RGB CHW image, so that the returned
  object retains no C values;
* a deterministic C-only perturbation for the invariance smoke that changes
  every finite C value, never relies on clipping, and leaves A/B bitwise
  unchanged;
* validation of proposed birth-candidate flat indices (1-D, integer, in range,
  unique, all in A).

Design constraints:

* numpy and the standard library only; no torch, no upstream Image-GS import,
  no GPU code path;
* no module-level mutable state, caches or random number generators; every
  function is a deterministic function of its arguments;
* inputs are never mutated; returned arrays are fresh copies marked read-only;
* clean truth is never read here (callers pass the noisy target only).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

FOLD_A = 0
FOLD_B = 1
FOLD_C = 2
FOLD_NAMES = ("A", "B", "C")
RGB_CHANNELS = 3

# Perturbation magnitudes lie in [low, high]; high <= 0.5 guarantees that a
# value inside [0, 1] stays inside [0, 1] without any clipping (see
# perturb_c_only).
DEFAULT_C_DELTA_RANGE = (0.01, 0.05)
_MAX_DELTA = 0.5
_DELTA_LEVELS = 17
_HASH_DOMAIN = b"P1817-fold-boundary-AB-v1"


# ---------------------------------------------------------------------------
# Fold map and indices
# ---------------------------------------------------------------------------
def _check_size(name: str, value) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}.")
    if int(value) <= 0:
        raise ValueError(f"{name} must be positive, got {value}.")
    return int(value)


def fold_labels(height: int, width: int) -> np.ndarray:
    """Return an int64 (H, W) array with ``labels[y, x] = (x + 2*y) % 3``."""
    h = _check_size("height", height)
    w = _check_size("width", width)
    y = np.arange(h, dtype=np.int64)[:, None]
    x = np.arange(w, dtype=np.int64)[None, :]
    labels = (x + 2 * y) % 3
    labels.setflags(write=False)
    return labels


def fold_flat_indices(height: int, width: int) -> Dict[str, np.ndarray]:
    """Return sorted, disjoint, covering row-major flat indices per fold.

    Flat index convention: ``y * width + x`` (x = column, y = row), the same
    row-major order as upstream ``pixel_xy`` and ``image.reshape(C, H*W)``.
    """
    h = _check_size("height", height)
    w = _check_size("width", width)
    flat_labels = fold_labels(h, w).reshape(-1)
    out: Dict[str, np.ndarray] = {}
    for code, name in enumerate(FOLD_NAMES):
        idx = np.flatnonzero(flat_labels == code).astype(np.int64, copy=False)
        idx.setflags(write=False)
        out[name] = idx
    merged = np.concatenate([out[name] for name in FOLD_NAMES])
    if merged.size != h * w or np.unique(merged).size != h * w:
        raise RuntimeError("Fold indices are not a disjoint cover of the image.")
    return out


# ---------------------------------------------------------------------------
# A/B extraction (no C retained)
# ---------------------------------------------------------------------------
def _check_rgb_chw(arr: np.ndarray) -> Tuple[int, int, int]:
    if arr.ndim != 3:
        raise ValueError(f"Expected an RGB CHW array with ndim 3, got ndim {arr.ndim}.")
    c, h, w = arr.shape
    if c != RGB_CHANNELS:
        raise ValueError(f"Expected {RGB_CHANNELS} channels (CHW), got {c}.")
    if h <= 0 or w <= 0:
        raise ValueError(f"Image must be non-empty, got shape {arr.shape}.")
    if arr.dtype not in (np.dtype("float32"), np.dtype("float64")):
        raise TypeError(f"Expected float32 or float64 image, got dtype {arr.dtype}.")
    return c, h, w


@dataclass(frozen=True, eq=False)
class ABValues:
    """A- and B-fold values gathered from one RGB CHW image.

    ``a_values[:, i]`` is the RGB value at flat index ``a_index[i]``; likewise
    for B. No C value and no reference to the source image is retained.
    """

    height: int
    width: int
    a_index: np.ndarray
    b_index: np.ndarray
    a_values: np.ndarray
    b_values: np.ndarray


def split_ab_values(image_chw) -> ABValues:
    """Gather A and B values from an RGB CHW float image.

    Only the gathered A/B values are checked for finiteness; C values are not
    inspected (they may even be a NaN sentinel). Raises ValueError if any A or
    B value is non-finite.
    """
    arr = np.asarray(image_chw)
    c, h, w = _check_rgb_chw(arr)
    idx = fold_flat_indices(h, w)
    flat = arr.reshape(c, h * w)
    a_values = np.take(flat, idx["A"], axis=1).copy()
    b_values = np.take(flat, idx["B"], axis=1).copy()
    del flat
    if not np.all(np.isfinite(a_values)):
        raise ValueError("Non-finite value in A-fold target.")
    if not np.all(np.isfinite(b_values)):
        raise ValueError("Non-finite value in B-fold target.")
    a_index = idx["A"].copy()
    b_index = idx["B"].copy()
    for array in (a_index, b_index, a_values, b_values):
        array.setflags(write=False)
    return ABValues(
        height=h,
        width=w,
        a_index=a_index,
        b_index=b_index,
        a_values=a_values,
        b_values=b_values,
    )


def hash_ab_values(ab: ABValues) -> str:
    """SHA-256 over geometry, indices, dtypes, shapes and bytes of A/B data.

    Intended for invariance layer (i): the hash of every trainer-held target
    must be identical under a C-only perturbation.
    """
    digest = hashlib.sha256()
    digest.update(_HASH_DOMAIN)
    digest.update(f"|{ab.height}x{ab.width}|".encode("ascii"))
    for name in ("a_index", "b_index", "a_values", "b_values"):
        array = np.ascontiguousarray(getattr(ab, name))
        digest.update(f"{name}:{array.dtype.str}:{array.shape}|".encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# C-only perturbation for the invariance smoke
# ---------------------------------------------------------------------------
def _check_delta_range(delta_range: Sequence[float]) -> Tuple[float, float]:
    if len(delta_range) != 2:
        raise ValueError("delta_range must have exactly two entries (low, high).")
    low, high = float(delta_range[0]), float(delta_range[1])
    if not (np.isfinite(low) and np.isfinite(high)):
        raise ValueError("delta_range entries must be finite.")
    if not (0.0 < low <= high <= _MAX_DELTA):
        raise ValueError(
            f"delta_range must satisfy 0 < low <= high <= {_MAX_DELTA}, got {delta_range}."
        )
    return low, high


def c_delta_magnitudes(
    channels: int, count: int, delta_range: Sequence[float] = DEFAULT_C_DELTA_RANGE
) -> np.ndarray:
    """Deterministic strictly positive float64 magnitudes of shape (channels, count).

    ``mag[ch, k] = low + (high - low) * ((k + 5*ch) % 17) / 16``: varied across
    pixels and channels, never zero, never dependent on any RNG.
    """
    channels = _check_size("channels", channels)
    if isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)):
        raise TypeError("count must be an integer.")
    if count < 0:
        raise ValueError("count must be non-negative.")
    low, high = _check_delta_range(delta_range)
    k = np.arange(int(count), dtype=np.int64)[None, :]
    ch = np.arange(channels, dtype=np.int64)[:, None]
    level = (k + 5 * ch) % _DELTA_LEVELS
    return low + (high - low) * level.astype(np.float64) / (_DELTA_LEVELS - 1)


def perturb_c_only(
    image_chw, delta_range: Sequence[float] = DEFAULT_C_DELTA_RANGE
) -> np.ndarray:
    """Return a copy of an RGB CHW float image with only C-fold values changed.

    Each finite C value ``v`` becomes ``v + m`` if ``v <= 0.5`` else ``v - m``,
    with ``m`` from :func:`c_delta_magnitudes` (``0 < m <= 0.5``). The sign is
    chosen to move away from the nearer of 0 and 1, so values in [0, 1] stay in
    [0, 1] without clipping, and saturated pixels (0.0 or 1.0) still change.
    No clipping is ever applied, so no delta can be cancelled.

    Non-finite C values are left non-finite. A and B values are copied
    bitwise. Raises ValueError if any finite C value would be left unchanged
    (e.g. magnitude below float resolution) or would become non-finite.
    """
    arr = np.asarray(image_chw)
    c, h, w = _check_rgb_chw(arr)
    c_idx = fold_flat_indices(h, w)["C"]
    out_flat = np.array(arr, dtype=arr.dtype, copy=True, order="C").reshape(c, h * w)

    original_c = out_flat[:, c_idx]
    magnitude = c_delta_magnitudes(c, c_idx.size, delta_range).astype(arr.dtype)
    if np.any(~(magnitude > 0)):
        raise ValueError(f"Perturbation magnitude underflows in dtype {arr.dtype}.")
    sign = np.where(original_c > 0.5, -1.0, 1.0).astype(arr.dtype)
    perturbed_c = original_c + sign * magnitude

    finite = np.isfinite(original_c)
    if not np.any(finite):
        raise ValueError("C perturbation requires at least one finite C value.")
    if np.any(finite & (perturbed_c == original_c)):
        raise ValueError("C perturbation would leave some finite C values unchanged.")
    if np.any(finite & ~np.isfinite(perturbed_c)):
        raise ValueError("C perturbation would make some finite C values non-finite.")

    out_flat[:, c_idx] = perturbed_c
    return out_flat.reshape(c, h, w)


# ---------------------------------------------------------------------------
# Proposal validation
# ---------------------------------------------------------------------------
def validate_proposal_indices(
    indices, height: int, width: int, expected_count: Optional[int] = None
) -> np.ndarray:
    """Validate proposed birth-candidate flat indices and return them as int64.

    Requirements: 1-D, non-empty, integer (not bool) dtype, within
    ``[0, height*width)``, unique, and every index in fold A. Order is
    preserved (the matched control takes the first K). If ``expected_count``
    is given, the length must match it exactly. Raises TypeError/ValueError.
    """
    h = _check_size("height", height)
    w = _check_size("width", width)
    n_pixels = h * w
    arr = np.asarray(indices)
    if arr.ndim != 1:
        raise ValueError(f"Proposal indices must be 1-D, got ndim {arr.ndim}.")
    if arr.size == 0:
        raise ValueError("Proposal indices are empty.")
    if arr.dtype == np.bool_ or not np.issubdtype(arr.dtype, np.integer):
        raise TypeError(f"Proposal indices must have integer dtype, got {arr.dtype}.")
    if np.any(arr < 0):
        raise ValueError("Proposal indices contain negative values.")
    if np.any(arr >= n_pixels):
        raise ValueError(f"Proposal indices exceed the image size {n_pixels}.")
    idx = arr.astype(np.int64)
    n_unique = np.unique(idx).size
    if n_unique != idx.size:
        raise ValueError(
            f"Proposal indices contain {idx.size - n_unique} duplicate entries."
        )
    flat_labels = fold_labels(h, w).reshape(-1)
    outside_a = idx[flat_labels[idx] != FOLD_A]
    if outside_a.size:
        raise ValueError(
            f"{outside_a.size} proposal indices are not in fold A "
            f"(first: {int(outside_a[0])})."
        )
    if expected_count is not None:
        expected = _check_size("expected_count", expected_count)
        if idx.size != expected:
            raise ValueError(
                f"Expected {expected} proposal indices, got {idx.size}."
            )
    out = idx.copy()
    out.setflags(write=False)
    return out
