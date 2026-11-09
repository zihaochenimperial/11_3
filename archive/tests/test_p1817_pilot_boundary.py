"""CPU checks for the experimental pilot's integration; not a launch gate."""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from p1817_holdout_birth_pilot import P1817HoldoutBirthPilot


class PilotBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.model = P1817HoldoutBirthPilot.__new__(P1817HoldoutBirthPilot)
        torch.nn.Module.__init__(self.model)
        self.model.img_h = 192
        self.model.img_w = 192
        self.model.device = "cpu"
        self.model.dtype = torch.float32
        self.model.gamma = 1.0
        self.model.block_h = self.model.block_w = 16
        self.model.perturb_c = False
        self.model._build_fold_mask()
        self.model.l2_loss_ratio = 1.0

    def test_flat_indices_match_fold_masks(self):
        for name, mask in (("A", self.model.a_mask_bool),
                           ("B", self.model.b_mask_bool),
                           ("C", self.model.c_mask_bool)):
            expected = torch.nonzero(mask.reshape(-1), as_tuple=False).squeeze(1).numpy()
            np.testing.assert_array_equal(self.model.fold_indices[name], expected)
            self.assertEqual(len(expected), 12288)

    def test_a_loss_ignores_nan_c_and_has_zero_b_c_gradients(self):
        target = torch.zeros((3, 192, 192), dtype=torch.float32)
        target[:, self.model.c_mask_bool] = float("nan")
        target[:, self.model.b_mask_bool] = 0.75
        self.model.gt_images = target
        prediction = torch.full_like(target, 0.25, requires_grad=True)
        self.model._get_total_loss(prediction)
        self.model.total_loss.backward()
        self.assertTrue(torch.isfinite(self.model.total_loss))
        self.assertTrue(torch.isfinite(prediction.grad).all())
        self.assertEqual(torch.count_nonzero(prediction.grad[:, self.model.b_mask_bool]).item(), 0)
        self.assertEqual(torch.count_nonzero(prediction.grad[:, self.model.c_mask_bool]).item(), 0)
        self.assertGreater(torch.count_nonzero(prediction.grad[:, self.model.a_mask_bool]).item(), 0)

    def test_loader_discards_c_and_is_invariant_to_c_perturbation(self):
        pixels = np.random.default_rng(123).integers(0, 256, (192, 192, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "noisy.png"
            Image.fromarray(pixels).save(path)
            self.model._load_target_images(str(path))
            baseline = self.model.gt_images.clone()
            self.assertTrue(torch.isnan(baseline[:, self.model.c_mask_bool]).all())
            self.assertTrue(torch.isfinite(baseline[:, self.model.a_mask_bool]).all())
            self.assertTrue(torch.isfinite(baseline[:, self.model.b_mask_bool]).all())
            self.model.perturb_c = True
            self.model._load_target_images(str(path))
            torch.testing.assert_close(
                self.model.gt_images, baseline, rtol=0, atol=0, equal_nan=True
            )


if __name__ == "__main__":
    unittest.main()
