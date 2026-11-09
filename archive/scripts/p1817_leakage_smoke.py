"""CPU-only invariance checks for the proposed A/B/C selection interface.

This deliberately uses simple fixed candidates, not Image-GS. It verifies the
data-flow contract before implementing held-out Gaussian birth.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def candidates(noisy: np.ndarray, fit: np.ndarray) -> np.ndarray:
    coordinates = np.linspace(-1.0, 1.0, noisy.size)
    center = float(np.mean(noisy[fit]))
    slope = float(np.mean(noisy[fit] * coordinates[fit]))
    return np.stack([
        np.full(noisy.shape, center),
        center + 0.5 * slope * coordinates,
        center + slope * coordinates,
    ])


def select(noisy: np.ndarray, proposed: np.ndarray, selection: np.ndarray) -> int:
    losses = np.mean((proposed[:, selection] - noisy[selection]) ** 2, axis=1)
    return int(np.argmin(losses))


def one_rotation(noisy: np.ndarray, target_fold: int) -> dict[str, object]:
    target = np.arange(noisy.size) % 3 == target_fold
    fit = np.arange(noisy.size) % 3 == (target_fold + 1) % 3
    selection = np.arange(noisy.size) % 3 == (target_fold + 2) % 3
    assert not np.any(target & fit) and not np.any(target & selection)
    assert not np.any(fit & selection)
    proposed = candidates(noisy, fit)
    chosen = select(noisy, proposed, selection)

    target_changed = noisy.copy()
    target_changed[target] += 10.0
    assert np.array_equal(proposed, candidates(target_changed, fit))
    assert chosen == select(target_changed, candidates(target_changed, fit), selection)
    assert np.array_equal(proposed[chosen, target], candidates(target_changed, fit)[chosen, target])

    selection_changed = noisy.copy()
    selection_changed[selection] -= 7.0
    assert np.array_equal(proposed, candidates(selection_changed, fit))

    fit_changed = noisy.copy()
    fit_changed[fit] += 5.0
    assert not np.array_equal(proposed, candidates(fit_changed, fit))

    # A deliberately invalid proposal reads the target values; the same check catches it.
    leaky = proposed + float(np.mean(noisy[target]))
    leaky_after = candidates(target_changed, fit) + float(np.mean(target_changed[target]))
    assert not np.array_equal(leaky[:, target], leaky_after[:, target])

    return {
        "target_fold": target_fold,
        "fit_indices": np.flatnonzero(fit).tolist(),
        "selection_indices": np.flatnonzero(selection).tolist(),
        "target_indices": np.flatnonzero(target).tolist(),
        "chosen_candidate": chosen,
        "target_invariance": True,
        "selection_values_do_not_change_candidates": True,
        "fit_values_change_candidates": True,
        "deliberate_target_leak_detected": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rng = np.random.default_rng(123)
    clean = np.linspace(0.2, 0.8, 18)
    noisy = clean + rng.normal(0, 0.1, clean.size)
    rotations = [one_rotation(noisy, fold) for fold in range(3)]
    result = {
        "classification": "CPU evaluator data-flow smoke; fixed candidates, no Gaussian method",
        "seed": 123,
        "clean_sha256": hashlib.sha256(clean.tobytes()).hexdigest(),
        "noisy_sha256": hashlib.sha256(noisy.tobytes()).hexdigest(),
        "rotations": rotations,
        "status": "passed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rotations": len(rotations)}))


if __name__ == "__main__":
    main()
