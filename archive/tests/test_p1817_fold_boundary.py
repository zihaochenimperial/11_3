"""CPU unit tests for scripts/p1817_fold_boundary.py (preparation patch only).

These tests use synthetic numpy arrays only: no clean truth, no upstream
Image-GS import, no GPU. Passing them does not make the GPU pilot launchable.
"""

import ast
from dataclasses import replace
import pathlib
import sys
import unittest

import numpy as np

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
MODULE_PATH = SCRIPTS_DIR / "p1817_fold_boundary.py"
sys.path.insert(0, str(SCRIPTS_DIR))

import p1817_fold_boundary as fb  # noqa: E402

H = W = 192
PER_FOLD = 12288


def synthetic_image(height=H, width=W, dtype=np.float32, seed=0):
    """Deterministic synthetic RGB CHW image in [0, 1] including saturation."""
    rng = np.random.default_rng(seed)
    img = rng.uniform(0.0, 1.0, size=(3, height, width)).astype(dtype)
    img[:, ::7, :] = 0.0
    img[:, :, ::11] = 1.0
    img[1, 3::13, :] = 0.5
    return img


class ModuleBoundaryTest(unittest.TestCase):
    def test_imports_only_numpy_and_stdlib(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        allowed = {"__future__", "hashlib", "dataclasses", "typing", "numpy"}
        self.assertTrue(imported <= allowed, f"Unexpected imports: {imported - allowed}")


class FoldLabelTest(unittest.TestCase):
    def test_formula_matches_brute_force(self):
        labels = fb.fold_labels(7, 5)
        self.assertEqual(labels.shape, (7, 5))
        self.assertEqual(labels.dtype, np.int64)
        for y in range(7):
            for x in range(5):
                self.assertEqual(labels[y, x], (x + 2 * y) % 3)

    def test_known_corner_values(self):
        labels = fb.fold_labels(H, W)
        self.assertEqual(labels[0, 0], fb.FOLD_A)
        self.assertEqual(labels[0, 1], fb.FOLD_B)
        self.assertEqual(labels[0, 2], fb.FOLD_C)
        self.assertEqual(labels[1, 0], fb.FOLD_C)  # (0 + 2) % 3
        self.assertEqual(labels[2, 0], fb.FOLD_B)  # (0 + 4) % 3

    def test_labels_read_only(self):
        labels = fb.fold_labels(4, 4)
        with self.assertRaises(ValueError):
            labels[0, 0] = 1

    def test_interior_a_pixel_has_two_b_and_two_c_neighbours(self):
        labels = fb.fold_labels(H, W)
        ys, xs = np.nonzero(labels[1:-1, 1:-1] == fb.FOLD_A)
        ys, xs = ys + 1, xs + 1
        neigh = np.stack(
            [labels[ys - 1, xs], labels[ys + 1, xs], labels[ys, xs - 1], labels[ys, xs + 1]]
        )
        self.assertTrue(np.all((neigh == fb.FOLD_B).sum(axis=0) == 2))
        self.assertTrue(np.all((neigh == fb.FOLD_C).sum(axis=0) == 2))

    def test_invalid_sizes(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                fb.fold_labels(bad, 4)
            with self.assertRaises(ValueError):
                fb.fold_flat_indices(4, bad)
        for bad in (1.5, "3", True, None):
            with self.assertRaises(TypeError):
                fb.fold_labels(bad, 4)


class FoldIndexTest(unittest.TestCase):
    def test_192_partition_counts_disjoint_cover(self):
        idx = fb.fold_flat_indices(H, W)
        self.assertEqual(set(idx), {"A", "B", "C"})
        for name in fb.FOLD_NAMES:
            self.assertEqual(idx[name].dtype, np.int64)
            self.assertEqual(idx[name].ndim, 1)
            self.assertEqual(idx[name].size, PER_FOLD, name)
            self.assertEqual(np.unique(idx[name]).size, PER_FOLD, name)
            self.assertTrue(np.all(np.diff(idx[name]) > 0), f"{name} not sorted")
        self.assertEqual(np.intersect1d(idx["A"], idx["B"]).size, 0)
        self.assertEqual(np.intersect1d(idx["A"], idx["C"]).size, 0)
        self.assertEqual(np.intersect1d(idx["B"], idx["C"]).size, 0)
        union = np.concatenate([idx["A"], idx["B"], idx["C"]])
        np.testing.assert_array_equal(np.sort(union), np.arange(H * W))

    def test_flat_indices_are_row_major_y_times_w_plus_x(self):
        idx = fb.fold_flat_indices(H, W)
        labels = fb.fold_labels(H, W)
        for code, name in enumerate(fb.FOLD_NAMES):
            ys, xs = np.divmod(idx[name], W)
            self.assertTrue(np.all((xs + 2 * ys) % 3 == code), name)
            self.assertTrue(np.all(labels[ys, xs] == code), name)
        # Explicit spot checks: (y=1, x=1) -> flat 193 is (1 + 2) % 3 = 0 (A).
        self.assertIn(1 * W + 1, set(idx["A"].tolist()))
        self.assertIn(1 * W + 0, set(idx["C"].tolist()))

    def test_non_square_cover(self):
        for h, w in ((5, 7), (1, 1), (2, 3), (13, 4)):
            idx = fb.fold_flat_indices(h, w)
            union = np.concatenate([idx[n] for n in fb.FOLD_NAMES])
            np.testing.assert_array_equal(np.sort(union), np.arange(h * w))

    def test_indices_read_only_and_fresh_per_call(self):
        first = fb.fold_flat_indices(6, 6)
        with self.assertRaises(ValueError):
            first["A"][0] = 5
        second = fb.fold_flat_indices(6, 6)
        self.assertFalse(np.shares_memory(first["A"], second["A"]))


class SplitABTest(unittest.TestCase):
    def test_values_and_shapes(self):
        img = synthetic_image()
        ab = fb.split_ab_values(img)
        self.assertEqual((ab.height, ab.width), (H, W))
        self.assertEqual(ab.a_values.shape, (3, PER_FOLD))
        self.assertEqual(ab.b_values.shape, (3, PER_FOLD))
        self.assertEqual(ab.a_values.dtype, img.dtype)
        idx = fb.fold_flat_indices(H, W)
        np.testing.assert_array_equal(ab.a_index, idx["A"])
        np.testing.assert_array_equal(ab.b_index, idx["B"])
        ya, xa = np.divmod(ab.a_index, W)
        yb, xb = np.divmod(ab.b_index, W)
        np.testing.assert_array_equal(ab.a_values, img[:, ya, xa])
        np.testing.assert_array_equal(ab.b_values, img[:, yb, xb])

    def test_no_c_values_retained(self):
        img = np.zeros((3, H, W), dtype=np.float64)
        labels = fb.fold_labels(H, W)
        img[:, labels == fb.FOLD_A] = 0.25
        img[:, labels == fb.FOLD_B] = 0.75
        img[:, labels == fb.FOLD_C] = np.nan  # C sentinel must not be needed
        ab = fb.split_ab_values(img)  # must not raise: C is not inspected
        self.assertTrue(np.all(ab.a_values == 0.25))
        self.assertTrue(np.all(ab.b_values == 0.75))
        for array in (ab.a_index, ab.b_index, ab.a_values, ab.b_values):
            self.assertFalse(np.shares_memory(array, img))
        self.assertEqual(np.intersect1d(ab.a_index, fb.fold_flat_indices(H, W)["C"]).size, 0)
        self.assertEqual(np.intersect1d(ab.b_index, fb.fold_flat_indices(H, W)["C"]).size, 0)
        fields = set(vars(ab))
        self.assertEqual(
            fields, {"height", "width", "a_index", "b_index", "a_values", "b_values"}
        )

    def test_output_independent_of_later_input_mutation(self):
        img = synthetic_image(dtype=np.float64)
        ab = fb.split_ab_values(img)
        before = fb.hash_ab_values(ab)
        img[:] = 123.0
        self.assertEqual(fb.hash_ab_values(ab), before)
        with self.assertRaises(ValueError):
            ab.a_values[0, 0] = 0.0

    def test_split_accepts_non_contiguous_input(self):
        img = synthetic_image(dtype=np.float64)
        hwc = np.ascontiguousarray(np.transpose(img, (1, 2, 0)))
        view_chw = np.transpose(hwc, (2, 0, 1))  # non-contiguous CHW view
        self.assertFalse(view_chw.flags["C_CONTIGUOUS"])
        self.assertEqual(
            fb.hash_ab_values(fb.split_ab_values(view_chw)),
            fb.hash_ab_values(fb.split_ab_values(img)),
        )

    def test_negative_inputs(self):
        with self.assertRaises(ValueError):
            fb.split_ab_values(np.zeros((H, W), dtype=np.float32))
        with self.assertRaises(ValueError):
            fb.split_ab_values(np.zeros((4, H, W), dtype=np.float32))
        with self.assertRaises(ValueError):
            fb.split_ab_values(np.zeros((1, H, W), dtype=np.float32))
        with self.assertRaises(TypeError):
            fb.split_ab_values(np.zeros((3, H, W), dtype=np.uint8))
        for dtype in (np.float16, np.longdouble):
            with self.assertRaises(TypeError):
                fb.split_ab_values(np.zeros((3, H, W), dtype=dtype))
        img = synthetic_image()
        img[0, 0, 0] = np.nan  # (x=0, y=0) is A
        with self.assertRaises(ValueError):
            fb.split_ab_values(img)
        img = synthetic_image()
        img[2, 0, 1] = np.inf  # (x=1, y=0) is B
        with self.assertRaises(ValueError):
            fb.split_ab_values(img)


    def test_ab_hash_changes_with_a_and_b_values(self):
        img = synthetic_image(dtype=np.float32)
        baseline = fb.hash_ab_values(fb.split_ab_values(img))
        for column in (0, 1):
            altered = img.copy()
            altered[0, 0, column] += np.float32(0.01)
            self.assertNotEqual(fb.hash_ab_values(fb.split_ab_values(altered)), baseline)

    def test_ab_hash_covers_geometry_dtype_order_and_shape(self):
        ab = fb.split_ab_values(synthetic_image(dtype=np.float32))
        baseline = fb.hash_ab_values(ab)
        variants = (
            replace(ab, height=ab.height + 1),
            replace(ab, a_index=ab.a_index[::-1].copy()),
            replace(ab, a_values=ab.a_values.astype(np.float64)),
            replace(ab, a_values=ab.a_values.reshape(-1)),
        )
        for variant in variants:
            self.assertNotEqual(fb.hash_ab_values(variant), baseline)


class PerturbCTest(unittest.TestCase):
    def assert_c_only_change(self, img, out):
        labels = fb.fold_labels(img.shape[1], img.shape[2])
        c_mask = labels == fb.FOLD_C
        ab_mask = ~c_mask
        orig_c, new_c = img[:, c_mask], out[:, c_mask]
        finite = np.isfinite(orig_c)
        self.assertTrue(np.all(new_c[finite] != orig_c[finite]), "a finite C value is unchanged")
        # A/B bitwise identical.
        self.assertEqual(img[:, ab_mask].tobytes(), out[:, ab_mask].tobytes())

    def test_changes_every_c_value_and_preserves_ab(self):
        for dtype in (np.float32, np.float64):
            img = synthetic_image(dtype=dtype, seed=1)
            out = fb.perturb_c_only(img)
            self.assertEqual(out.dtype, img.dtype)
            self.assertEqual(out.shape, img.shape)
            self.assert_c_only_change(img, out)
            self.assertEqual(
                fb.hash_ab_values(fb.split_ab_values(img)),
                fb.hash_ab_values(fb.split_ab_values(out)),
            )

    def test_saturated_values_change_without_clipping(self):
        for value in (0.0, 1.0, 0.5,
                      np.nextafter(np.float32(0.5), np.float32(0)),
                      np.nextafter(np.float32(0.5), np.float32(1))):
            img = np.full((3, H, W), value, dtype=np.float32)
            out = fb.perturb_c_only(img)
            self.assert_c_only_change(img, out)
            self.assertGreaterEqual(float(out.min()), 0.0)
            self.assertLessEqual(float(out.max()), 1.0)
            delta = np.abs(out.astype(np.float64) - img.astype(np.float64))
            c_mask = fb.fold_labels(H, W) == fb.FOLD_C
            self.assertGreater(float(delta[:, c_mask].min()), 0.009)

    def test_range_preserved_and_delta_bounds(self):
        img = synthetic_image(dtype=np.float64, seed=2)
        out = fb.perturb_c_only(img, delta_range=(0.02, 0.5))
        self.assertGreaterEqual(float(out.min()), 0.0)
        self.assertLessEqual(float(out.max()), 1.0)
        c_mask = fb.fold_labels(H, W) == fb.FOLD_C
        delta = np.abs(out - img)[:, c_mask]
        self.assertGreaterEqual(float(delta.min()), 0.02 - 1e-12)
        self.assertLessEqual(float(delta.max()), 0.5 + 1e-12)

    def test_deterministic_and_input_not_mutated(self):
        img = synthetic_image(seed=3)
        snapshot = img.copy()
        out1 = fb.perturb_c_only(img)
        out2 = fb.perturb_c_only(img)
        self.assertEqual(out1.tobytes(), out2.tobytes())
        self.assertEqual(img.tobytes(), snapshot.tobytes())
        self.assertFalse(np.shares_memory(out1, img))

    def test_magnitudes_positive_and_varied(self):
        mag = fb.c_delta_magnitudes(3, PER_FOLD)
        self.assertEqual(mag.shape, (3, PER_FOLD))
        self.assertTrue(np.all(mag >= 0.01))
        self.assertTrue(np.all(mag <= 0.05))
        self.assertGreater(np.unique(mag).size, 10)
        self.assertFalse(np.array_equal(mag[0], mag[1]))
        np.testing.assert_array_equal(mag, fb.c_delta_magnitudes(3, PER_FOLD))

    def test_non_finite_c_left_non_finite_and_finite_c_changed(self):
        img = synthetic_image(dtype=np.float64, seed=4)
        img[0, 0, 2] = np.nan  # (x=2, y=0) is C
        img[1, 1, 0] = np.inf  # (x=0, y=1) is C
        img[2, 1, 0] = -np.inf
        out = fb.perturb_c_only(img)
        self.assertTrue(np.isnan(out[0, 0, 2]))
        self.assertEqual(out[1, 1, 0], np.inf)
        self.assertEqual(out[2, 1, 0], -np.inf)
        self.assert_c_only_change(img, out)

    def test_all_nonfinite_or_empty_c_is_rejected(self):
        image = synthetic_image(dtype=np.float32)
        image[:, fb.fold_labels(H, W) == fb.FOLD_C] = np.nan
        with self.assertRaises(ValueError):
            fb.perturb_c_only(image)
        with self.assertRaises(ValueError):
            fb.perturb_c_only(np.zeros((3, 1, 1), dtype=np.float32))

    def test_float32_delta_too_small_to_change_value_is_rejected(self):
        image = np.full((3, H, W), 0.5, dtype=np.float32)
        with self.assertRaises(ValueError):
            fb.perturb_c_only(image, delta_range=(1e-12, 1e-12))

    def test_unchangeable_finite_c_value_raises(self):
        img = synthetic_image(dtype=np.float64, seed=5)
        img[0, 0, 2] = 1e20  # C pixel; 1e20 - 0.05 == 1e20 in float64
        with self.assertRaises(ValueError):
            fb.perturb_c_only(img)

    def test_invalid_delta_ranges_and_inputs(self):
        img = synthetic_image()
        for bad in ((0.0, 0.05), (-0.01, 0.05), (0.05, 0.01), (0.01, 0.6),
                    (0.01, np.nan), (0.01,), (0.01, 0.02, 0.03)):
            with self.assertRaises(ValueError, msg=str(bad)):
                fb.perturb_c_only(img, delta_range=bad)
        with self.assertRaises(TypeError):
            fb.perturb_c_only(np.zeros((3, 8, 8), dtype=np.int32))
        with self.assertRaises(ValueError):
            fb.perturb_c_only(np.zeros((8, 8), dtype=np.float32))


class ProposalValidationTest(unittest.TestCase):
    def setUp(self):
        self.a_idx = fb.fold_flat_indices(H, W)["A"]
        self.b_idx = fb.fold_flat_indices(H, W)["B"]
        self.c_idx = fb.fold_flat_indices(H, W)["C"]

    def test_valid_pool_of_256_preserves_order(self):
        rng = np.random.default_rng(123)
        pool = rng.choice(self.a_idx, size=256, replace=False)
        out = fb.validate_proposal_indices(pool, H, W, expected_count=256)
        self.assertEqual(out.dtype, np.int64)
        np.testing.assert_array_equal(out, pool)
        self.assertFalse(np.shares_memory(out, pool))
        with self.assertRaises(ValueError):
            out[0] = 0

    def test_accepts_python_list_and_unsigned(self):
        pool = [int(i) for i in self.a_idx[:5]]
        np.testing.assert_array_equal(fb.validate_proposal_indices(pool, H, W), pool)
        out = fb.validate_proposal_indices(self.a_idx[:5].astype(np.uint32), H, W)
        self.assertEqual(out.dtype, np.int64)

    def test_duplicates_rejected(self):
        pool = np.concatenate([self.a_idx[:10], self.a_idx[3:4]])
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(pool, H, W)

    def test_b_or_c_index_rejected(self):
        for intruder in (self.b_idx[7], self.c_idx[7]):
            pool = np.concatenate([self.a_idx[:10], [intruder]])
            with self.assertRaises(ValueError):
                fb.validate_proposal_indices(pool, H, W)

    def test_interleaved_yx_pairs_rejected(self):
        # Regression for preflight blocker 1: nonzero(mask).view(-1) produces
        # interleaved (y, x) pairs; for the A-fold they contain non-A flats
        # and/or duplicates, so validation must fail.
        ys, xs = np.nonzero(fb.fold_labels(H, W) == fb.FOLD_A)
        interleaved = np.stack([ys, xs], axis=1).reshape(-1)[:512]
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(interleaved, H, W)

    def test_out_of_range_and_negative_rejected(self):
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices([0, -3], H, W)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices([0, H * W], H, W)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(np.array([0, 2**63 + 3], dtype=np.uint64), H, W)

    def test_bad_dtype_shape_and_count_rejected(self):
        with self.assertRaises(TypeError):
            fb.validate_proposal_indices(self.a_idx[:4].astype(np.float64), H, W)
        with self.assertRaises(TypeError):
            fb.validate_proposal_indices(np.array([True, False]), H, W)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(self.a_idx[:4].reshape(2, 2), H, W)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(np.array([], dtype=np.int64), H, W)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(self.a_idx[:255], H, W, expected_count=256)
        with self.assertRaises(ValueError):
            fb.validate_proposal_indices(self.a_idx[:4], 0, W)


if __name__ == "__main__":
    unittest.main()
