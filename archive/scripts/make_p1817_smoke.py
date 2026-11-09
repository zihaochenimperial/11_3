"""Create one tiny, deterministic clean/noisy image pair for Image-GS plumbing."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=int, default=64)
    args = parser.parse_args()
    if args.size < 32:
        raise ValueError("Image side must be at least 32 pixels.")
    args.out.mkdir(parents=True, exist_ok=True)

    height = width = args.size
    clean = np.empty((height, width, 3), dtype=np.uint8)
    clean[:, : width // 2] = (45, 75, 110)
    clean[:, width // 2 :] = (190, 160, 120)
    for column in range(width):
        clean[3 * height // 4 :, column] = (
            (40, 40, 40) if column % 8 < 4 else (220, 220, 220)
        )

    seed = 123
    sigma_8bit = 25.0
    rng = np.random.default_rng(seed)
    noisy = np.clip(
        np.rint(clean.astype(np.float32) + rng.normal(0, sigma_8bit, clean.shape)),
        0,
        255,
    ).astype(np.uint8)

    clean_path = args.out / f"clean{width}.png"
    noisy_path = args.out / f"noisy{width}_sigma25_seed123.png"
    Image.fromarray(clean, mode="RGB").save(clean_path)
    Image.fromarray(noisy, mode="RGB").save(noisy_path)
    manifest = {
        "purpose": "Image-GS pipeline smoke only; not a development or independent test set",
        "shape_hwc": [height, width, 3],
        "noise": "independent Gaussian per pixel/channel, rounded and clipped to uint8",
        "sigma_8bit": sigma_8bit,
        "seed": seed,
        "clean_sha256": sha256(clean_path),
        "noisy_sha256": sha256(noisy_path),
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
