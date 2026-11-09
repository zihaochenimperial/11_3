"""F0 study configuration: single frozen dataclass for all tunables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class F0Config:
    """All tunable constants for the F0 CPU mechanism study."""

    H: int = 64
    W: int = 64
    sigma0: float = 0.08
    K0: int = 24
    birth_rounds: int = 3
    births_per_round: int = 8
    steps_per_stage: int = 150
    lr_xy: float = 5e-3
    lr_logscale: float = 2e-2
    lr_rot: float = 2e-2
    lr_val: float = 5e-2
    smooth_sigma_px: float = 1.5
    init_scale_px: float = 3.0
    birth_scale_px: float = 2.0
    S_grid: tuple = (8, 16, 64, 256, 1024)
    M: int = 256
    entropy: int = 20261105
    eps_frozen_rel: float = 0.01
    plin_grid: int = 16
    plin_scales_px: tuple = (1.5, 2.5, 4.0, 6.0)
    plin_rounds: int = 3


def cfg_hash(cfg: F0Config) -> str:
    """SHA-256 of the sorted JSON representation of a config."""
    payload = json.dumps(asdict(cfg), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
