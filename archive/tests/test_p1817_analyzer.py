"""CPU tests for scripts/analyze_p1817_holdout_birth.py on synthetic artifacts.

These are infrastructure tests only. The synthetic images, renders, RNG
records and timings are fabricated fixtures, not pilot outputs, and say
nothing about the method.

The fixture is deliberately independent of the evaluator's own helpers where
it matters: trainer-input hashes are recomputed here from the decoded PNG,
RNG records follow the pilot's ``capture_rng_state`` layout using real numpy
and python MT19937 states, invariance evidence is persisted as measurements
(not booleans only), and every phase carries wall-clock and monotonic timing.
"""

import contextlib
import copy
import hashlib
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import analyze_p1817_holdout_birth as an  # noqa: E402
from p1817_fold_boundary import (  # noqa: E402
    fold_flat_indices,
    fold_labels,
    hash_ab_values,
    perturb_c_only,
    split_ab_values,
)

H = W = 192
SEED = 123
FOLD_HELPER_SHA = hashlib.sha256((SCRIPTS / "p1817_fold_boundary.py").read_bytes()).hexdigest()
PILOT_SHA = "5" * 64
DEVICE = "cuda:0"
VERSIONS = {"python": "3.11.9", "torch": "2.4.1", "numpy": "1.26.4",
            "platform": "Linux-test", "hostname": "fixture-host",
            "cuda": "12.1", "cuda_device_name": "Fixture GPU"}
# Literal copy of the documented invariance check names (catches silent renames).
CHECK_NAMES = (
    "cpu_ab_hash_equal_across_c", "trainer_target_hash_equal_across_c",
    "cpu_ab_hash_matches_prefix", "trainer_target_hash_matches_prefix",
    "base_forward_repeat_bitwise_stable", "augmented_forward_repeat_bitwise_stable",
    "base_forward_equal_across_models", "augmented_forward_equal_across_models",
    "pool_recompute_matches_saved", "rng_after_recompute_matches_saved",
    "scorer_repeat_bitwise_stable", "pool_recompute_equal_across_c",
    "rng_after_recompute_equal_across_c", "scores_equal_across_c", "selection_equal_across_c")
LEGACY_CHECK_NAMES = (
    "cpu_ab_hash_equal_across_c", "cpu_ab_hash_matches_prefix",
    "trainer_target_hash_equal_across_c", "forward_repeat_bitwise_stable",
    "forward_equal_across_models", "pool_recompute_equal_across_c",
    "pool_recompute_matches_saved", "scorer_repeat_bitwise_stable",
    "scores_equal_across_c", "selection_equal_across_c")
FORWARD_RUNS = ("normal_1", "normal_2", "cperturb_1", "cperturb_2")
PREFIX_FILES = ("prefix_params", "candidate_pool", "rng_before_pool", "rng_after_pool")
ARM_FILES = ("selection", "birth_params", "final_params", "final_render", "rng_continuation_start")
INV_FILES = ("scores", "pool_recompute_normal", "pool_recompute_cperturb",
             "rng_after_pool_recompute_normal", "rng_after_pool_recompute_cperturb")

# Serial schedule (seconds after T0): start, finish. Gaps of 5 s between phases.
T0 = 1_800_000_000.0
SCHEDULE = {"prefix": (0.0, 12.0), "invariance": (17.0, 20.0), "control_r1": (25.0, 29.0),
            "control_r2": (34.0, 38.5), "holdout": (43.5, 51.0)}
ARM_WALL = {"control_r1": 3.0, "control_r2": 3.5, "holdout": 6.0}


def _decode(path):
    """Independent decoder (PIL convert path, not the evaluator's loader)."""
    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"), dtype=np.float32)
    return (arr / np.float32(255)).transpose(2, 0, 1).copy()


def _trainer_target_hash(img):
    """Independent construction of the pilot's NaN-at-C trainer target hash."""
    safe = np.array(img, dtype=np.float32, copy=True)
    safe[:, fold_labels(H, W) == 2] = np.nan
    return hashlib.sha256(safe.tobytes()).hexdigest()


def _rng_record(np_state, py_state, torch_cpu, cuda_states):
    rec = {"np_keys": np.asarray(np_state[1], dtype=np.uint32),
           "np_pos": np.asarray(np_state[2], dtype=np.int64),
           "np_has_gauss": np.asarray(np_state[3], dtype=np.int64),
           "np_cached_gaussian": np.asarray(np_state[4], dtype=np.float64),
           "py_version": np.asarray(py_state[0], dtype=np.int64),
           "py_internal": np.asarray(py_state[1], dtype=np.int64),
           "py_gauss_is_none": np.asarray(py_state[2] is None),
           "py_gauss_next": np.asarray(0.0 if py_state[2] is None else py_state[2], dtype=np.float64),
           "torch_cpu": np.array(torch_cpu, dtype=np.uint8),
           "cuda_count": np.asarray(len(cuda_states), dtype=np.int64)}
    for i, s in enumerate(cuda_states):
        rec[f"cuda_{i}"] = np.array(s, dtype=np.uint8)
    return rec


def _entry(run_dir: Path, name: str, arrays):
    arrays = {k: np.ascontiguousarray(v) for k, v in arrays.items()}
    np.savez(run_dir / f"{name}.npz", **arrays)
    raw = (run_dir / f"{name}.npz").read_bytes()
    return {"file": f"{name}.npz", "sha256": hashlib.sha256(raw).hexdigest(),
            "content_hash": an.canonical_arrays_hash(arrays)}


def _timing(phase, kind):
    s, f = SCHEDULE[phase]
    wall = f - s
    if kind == "prefix":
        t = {"init": 1.0, "train_1_500": 8.5, "pool": 0.5, "prefix_wall": 10.0}
    elif kind == "invariance":
        t = {"invariance_wall": 2.0}
    else:
        aw = ARM_WALL[phase]
        t = {"setup": 0.5, "selection_and_birth": 0.5, "continuation_501_1000": aw - 1.5,
             "finalize_render": 0.5, "arm_wall": aw}
    t["process_wall"] = wall
    return t


def _base(kind, phase, noisy_sha, command):
    s, f = SCHEDULE[phase]
    return {"artifact_format": an.ARTIFACT_FORMAT, "kind": kind, "status": "completed",
            "classification": "auxiliary/development mechanism pilot",
            "seed": SEED, "device": DEVICE, "input_sha256": noisy_sha,
            "source_commit": an.EXPECTED_UPSTREAM_COMMIT, "source_license": "MIT",
            "pilot_script_sha256": PILOT_SHA, "fold_helper_sha256": FOLD_HELPER_SHA,
            "versions": dict(VERSIONS),
            "command": ["p1817_holdout_birth_pilot.py", *command, "--input", "noisy.png"],
            "implementation_config": copy.deepcopy(an.EXPECTED_IMPLEMENTATION_CONFIG),
            "initial_gaussians": 256, "final_gaussians": 320, "birth_step": 500,
            "birth_count": 64, "candidate_pool_size": 256, "max_steps": 1000,
            "process_started_unix": T0 + s, "finished_unix": T0 + f,
            "timing_sec": _timing(phase, kind)}


def _params(rng, n):
    return {k: rng.random((n, c)).astype(np.float32) for k, c in an.PARAM_COLS.items()}


class Campaign:
    """Writes a synthetic, internally consistent artifact tree.

    ``mutate(name, payload)`` edits arrays/manifest before files are written;
    ``edit_manifest(name, manifest)`` edits the manifest after the file table
    is built, immediately before it is written. Later phases derive their
    inputs from the (possibly mutated) prefix payload.
    """

    def __init__(self, root: Path, biases, mutate=None, skip=(), inv_result="passed",
                 edit_manifest=None):
        self.root = root
        rng = np.random.default_rng(7)
        clean8 = rng.integers(51, 205, (H, W, 3), dtype=np.uint8)
        noise = rng.normal(0, 25.0, (H, W, 3))
        noisy8 = np.clip(np.round(clean8 + noise), 0, 255).astype(np.uint8)
        self.clean_path, self.noisy_path = root / "clean.png", root / "noisy.png"
        Image.fromarray(clean8).save(self.clean_path)
        Image.fromarray(noisy8).save(self.noisy_path)
        self.clean_sha = hashlib.sha256(self.clean_path.read_bytes()).hexdigest()
        self.noisy_sha = hashlib.sha256(self.noisy_path.read_bytes()).hexdigest()
        noisy = _decode(self.noisy_path)
        clean = _decode(self.clean_path)
        self.ab_hash = hash_ab_values(split_ab_values(noisy))
        self.tt_hash = _trainer_target_hash(noisy)
        ab_pert = hash_ab_values(split_ab_values(perturb_c_only(noisy)))
        tt_pert = _trainer_target_hash(perturb_c_only(noisy))
        mutate = mutate or (lambda name, p: None)
        edit_manifest = edit_manifest or (lambda name, m: None)

        def write(run_dir, name, payload, names):
            mutate(name, payload)
            m = payload["manifest"]
            m["files"] = {n: _entry(run_dir, n, payload[n]) for n in names if n in payload}
            edit_manifest(name, m)
            (run_dir / "manifest.json").write_text(json.dumps(m))
            return m

        # RNG records in the capture_rng_state layout.
        rs = np.random.RandomState(SEED)
        rs.random_sample(5)
        np_before = rs.get_state()
        rs.random_sample(300)  # the pool draw advances numpy
        np_after = rs.get_state()
        py_state = random.Random(SEED).getstate()
        torch_cpu = rng.integers(0, 256, an.TORCH_CPU_RNG_BYTES, dtype=np.uint8)
        cuda_before = rng.integers(0, 256, an.CUDA_RNG_BYTES, dtype=np.uint8)
        cuda_after = cuda_before.copy()
        cuda_after[8] ^= 0x10  # Philox offset advanced by the on-device vis_feat draw

        # Prefix
        pdir = root / "prefix"
        pdir.mkdir()
        idx = np.sort(rng.choice(fold_flat_indices(H, W)["A"], 256, replace=False)).astype(np.int64)
        pool = _params(rng, 256)
        pool["xy"] = np.stack([(idx % W + 0.5) / W, (idx // W + 0.5) / H], 1).astype(np.float32)
        pool["scale"] = np.full((256, 2), 0.2, np.float32)
        pool["rot"] = np.zeros((256, 1), np.float32)
        pool["indices"] = idx
        counts = {name: int(np.sum(fold_labels(H, W) == code)) for code, name in enumerate("ABC")}
        manifest = dict(_base("prefix", "prefix", self.noisy_sha, ["prefix"]),
                        steps_completed=500, fold_counts=counts,
                        ab_hash=self.ab_hash, trainer_target_hash=self.tt_hash)
        payload = {"manifest": manifest, "prefix_params": _params(rng, 256), "candidate_pool": pool,
                   "rng_before_pool": _rng_record(np_before, py_state, torch_cpu, [cuda_before]),
                   "rng_after_pool": _rng_record(np_after, py_state, torch_cpu, [cuda_after])}
        m = write(pdir, "prefix", payload, PREFIX_FILES)
        pre, pool = payload["prefix_params"], payload["candidate_pool"]
        rng_after = payload["rng_after_pool"]
        p_ab, p_tt = m.get("ab_hash"), m.get("trainer_target_hash")
        ref = {"manifest_sha256": hashlib.sha256((pdir / "manifest.json").read_bytes()).hexdigest()}
        for key, fname in (("prefix_params_hash", "prefix_params"),
                           ("candidate_pool_hash", "candidate_pool"),
                           ("rng_before_pool_hash", "rng_before_pool"),
                           ("rng_after_pool_hash", "rng_after_pool")):
            ref[key] = an.canonical_arrays_hash(payload[fname])

        # Holdout scores are fixed first so invariance can persist the same values.
        h_scores = rng.normal(size=256).astype(np.float64)
        h_sel = np.argsort(-h_scores, kind="stable")[:64].astype(np.int64)

        # Arms
        for arm, role in an.ARMS.items():
            if arm in skip:
                continue
            adir = root / arm
            adir.mkdir()
            if role == "control":
                sel, scores = np.arange(64, dtype=np.int64), np.zeros(0, dtype=np.float64)
            else:
                sel, scores = h_sel.copy(), h_scores.copy()
            birth = {k: np.concatenate([pre[k], pool[k][sel]]) for k in an.PARAM_KEYS}
            final = {k: (v + 0.01).astype(np.float32) for k, v in birth.items()}
            render = (clean + np.float32(biases[arm])).astype(np.float32)
            manifest = dict(_base("arm", arm, self.noisy_sha, ["continue", "--arm", arm]),
                            arm=arm, role=role, prefix_ref=dict(ref), ab_hash=p_ab,
                            trainer_target_hash=p_tt, steps_completed=1000,
                            num_gaussians_final=320, peak_vram_bytes=0)
            payload = {"manifest": manifest,
                       "selection": {"selected": sel, "scores": scores},
                       "birth_params": birth, "final_params": final,
                       "final_render": {"render": render},
                       "rng_continuation_start": copy.deepcopy(rng_after)}
            write(adir, arm, payload, ARM_FILES)

        if "invariance" not in skip:
            idir = root / "invariance"
            idir.mkdir()
            same_c = p_ab == self.ab_hash and p_tt == self.tt_hash
            manifest = dict(
                _base("invariance", "invariance", self.noisy_sha, ["invariance"]),
                prefix_ref=dict(ref), invariance_result=inv_result,
                checks={k: True for k in CHECK_NAMES},
                cpu_ab_hash={"normal": p_ab, "cperturb": ab_pert if same_c else p_ab},
                trainer_target_hash_by_c={"normal": p_tt, "cperturb": tt_pert if same_c else p_tt},
                forward_sha256={"base": {r: "a" * 64 for r in FORWARD_RUNS},
                                "augmented": {r: "b" * 64 for r in FORWARD_RUNS}},
                peak_vram_bytes=0)
            scores = {}
            for r in ("normal_1", "normal_2", "cperturb"):
                scores[f"scores_{r}"] = h_scores.copy()
                scores[f"selected_{r}"] = h_sel.copy()
            payload = {"manifest": manifest, "scores": scores,
                       "pool_recompute_normal": copy.deepcopy(pool),
                       "pool_recompute_cperturb": copy.deepcopy(pool),
                       "rng_after_pool_recompute_normal": copy.deepcopy(rng_after),
                       "rng_after_pool_recompute_cperturb": copy.deepcopy(rng_after)}
            write(idir, "invariance", payload, INV_FILES)

    def evaluate(self, clean_sha=None, noisy_sha=None, loader=None):
        calls = []
        base_loader = loader or an.load_rgb8

        def tracking(path):
            calls.append(Path(path).name)
            return base_loader(path)

        report = an.evaluate(self.root, self.noisy_path, self.clean_path,
                             expected_noisy_sha=noisy_sha or self.noisy_sha,
                             expected_clean_sha=clean_sha or self.clean_sha,
                             image_loader=tracking)
        return report, calls


PASS_BIASES = {"control_r1": 0.05, "control_r2": 0.06, "holdout": 0.0}


def _on(target, fn):
    """mutate/edit hook applying ``fn`` only to phase ``target``."""
    def hook(name, obj):
        if name == target:
            fn(obj)
    return hook


class AnalyzerBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_campaign(self, **kw):
        return Campaign(self.root, kw.pop("biases", PASS_BIASES), **kw).evaluate()

    def assertDecision(self, report, decision, where=None):
        self.assertEqual(report["decision"], decision, report["problems"])
        if where is not None:
            self.assertIn(where, {p["where"] for p in report["problems"]}, report["problems"])

    def assertNothingRead(self, report, calls):
        self.assertFalse(report["noisy_read"])
        self.assertFalse(report["clean_truth_read"])
        self.assertEqual(calls, [])
        self.assertIsNone(report["metrics"])
        self.assertIsNone(report["criteria"])

    def assertCleanUnread(self, report, calls):
        self.assertFalse(report["clean_truth_read"])
        self.assertNotIn("clean.png", calls)
        self.assertIsNone(report["metrics"])
        self.assertIsNone(report["inputs"]["clean"]["sha256"])


class DecisionTests(AnalyzerBase):
    def test_clear_improvement_is_preliminary_pass_with_provenance(self):
        c = Campaign(self.root, PASS_BIASES)
        report, calls = c.evaluate()
        self.assertDecision(report, "preliminary_pass")
        self.assertEqual(report["problems"], [])
        self.assertEqual(calls, ["noisy.png", "clean.png"])
        for crit in report["criteria"].values():
            self.assertGreater(crit["improvement"], crit["control_noise_floor"])
        # Actual input, decoded-data, tool, contract and artifact identities.
        self.assertEqual(report["inputs"]["noisy"]["sha256"], c.noisy_sha)
        self.assertEqual(report["inputs"]["clean"]["sha256"], c.clean_sha)
        self.assertEqual(report["inputs"]["noisy"]["recomputed_trainer_inputs"],
                         {"ab_hash": {"normal": c.ab_hash, "cperturb": c.ab_hash},
                          "trainer_target_hash": {"normal": c.tt_hash, "cperturb": c.tt_hash}})
        self.assertIsNotNone(report["inputs"]["clean"]["decoded_content_hash"])
        self.assertEqual(report["tools"]["fold_helper_sha256"], FOLD_HELPER_SHA)
        self.assertEqual(report["tools"]["evaluator_sha256"], hashlib.sha256(
            (SCRIPTS / "analyze_p1817_holdout_birth.py").read_bytes()).hexdigest())
        for doc in report["contract_documents"].values():
            self.assertIsNotNone(doc["sha256"])
        self.assertEqual(set(report["artifacts"]), set(an.PHASES))
        prefix_manifest = (self.root / "prefix" / "manifest.json").read_bytes()
        self.assertEqual(report["artifacts"]["prefix"]["manifest_sha256"],
                         hashlib.sha256(prefix_manifest).hexdigest())
        self.assertEqual(report["implementation"]["pilot_script_sha256"], PILOT_SHA)
        self.assertEqual(report["implementation"]["implementation_config"],
                         an.EXPECTED_IMPLEMENTATION_CONFIG)
        self.assertFalse(report["frozen_input_hashes_used"])  # fixture images, not frozen ones

    def test_improvement_within_control_floor_is_no_go(self):
        report, _ = self.run_campaign(biases={"control_r1": 0.0, "control_r2": 0.1, "holdout": 0.05})
        self.assertDecision(report, "no_go")
        c = report["criteria"]["clean_C_mse"]
        self.assertGreater(c["improvement"], 0)
        self.assertFalse(c["passes"])

    def test_worse_holdout_is_no_go(self):
        report, _ = self.run_campaign(biases={"control_r1": 0.0, "control_r2": 0.0, "holdout": 0.1})
        self.assertDecision(report, "no_go")


class ArtifactTests(AnalyzerBase):
    def test_missing_arm_is_inconclusive_and_nothing_read(self):
        report, calls = self.run_campaign(skip=("holdout",))
        self.assertDecision(report, "inconclusive", "holdout")
        self.assertNothingRead(report, calls)
        self.assertIsNone(report["costs"])

    def test_missing_invariance_is_inconclusive(self):
        report, calls = self.run_campaign(skip=("invariance",))
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)
        self.assertIsNone(report["costs"])

    def test_failed_arm_status_is_inconclusive(self):
        report, calls = self.run_campaign(
            mutate=_on("control_r2", lambda p: p["manifest"].update(status="failed")))
        self.assertDecision(report, "inconclusive", "control_r2")
        self.assertNothingRead(report, calls)

    def test_missing_prefix_is_inconclusive(self):
        c = Campaign(self.root, PASS_BIASES)
        (self.root / "prefix" / "manifest.json").unlink()
        report, calls = c.evaluate()
        self.assertDecision(report, "inconclusive", "prefix")
        self.assertNothingRead(report, calls)

    def test_non_object_manifest_is_inconclusive(self):
        c = Campaign(self.root, PASS_BIASES)
        (self.root / "control_r1" / "manifest.json").write_text("[]")
        report, calls = c.evaluate()
        self.assertDecision(report, "inconclusive", "control_r1")
        self.assertNothingRead(report, calls)

    def test_file_table_not_a_dict_is_inconclusive(self):
        report, calls = self.run_campaign(
            edit_manifest=_on("holdout", lambda m: m.update(files="not-a-table")))
        self.assertDecision(report, "inconclusive", "holdout")
        self.assertNothingRead(report, calls)

    def test_file_entry_escaping_run_dir_is_invalid(self):
        def edit(m):
            m["files"]["selection"]["file"] = "../selection.npz"
        report, calls = self.run_campaign(edit_manifest=_on("holdout", edit))
        self.assertDecision(report, "invalid", "holdout")
        self.assertNothingRead(report, calls)

    def test_extra_npz_key_is_invalid(self):
        def mutate(p):
            p["selection"]["extra"] = np.zeros(1)
        report, calls = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "invalid", "holdout")
        self.assertNothingRead(report, calls)

    def test_pool_hash_mismatch_is_invalid(self):
        def mutate(p):
            p["manifest"]["prefix_ref"]["candidate_pool_hash"] = "0" * 64
        report, calls = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "invalid", "holdout")
        self.assertNothingRead(report, calls)

    def test_birth_not_from_shared_prefix_is_invalid(self):
        def mutate(p):
            p["birth_params"]["feat"][0, 0] += 1.0
        report, calls = self.run_campaign(mutate=_on("control_r1", mutate))
        self.assertDecision(report, "invalid", "control_r1")
        self.assertNothingRead(report, calls)

    def test_holdout_selection_rule_violation_is_invalid(self):
        def mutate(p):
            p["selection"]["selected"] = p["selection"]["selected"][::-1].copy()
        report, calls = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "invalid", "holdout")
        self.assertNothingRead(report, calls)

    def test_nonfinite_holdout_score_is_invalid(self):
        def mutate(p):
            p["selection"]["scores"][0] = np.nan
        report, _ = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "invalid", "holdout")

    def test_control_not_first_k_is_invalid(self):
        def mutate(p):
            p["selection"]["selected"] = np.arange(1, 65, dtype=np.int64)
        report, _ = self.run_campaign(mutate=_on("control_r2", mutate))
        self.assertDecision(report, "invalid", "control_r2")

    def test_pool_index_outside_a_is_invalid(self):
        b_index = int(fold_flat_indices(H, W)["B"][0])

        def mutate(p):
            pool = p["candidate_pool"]
            pool["indices"][0] = b_index
            pool["xy"][0] = [(b_index % W + 0.5) / W, (b_index // W + 0.5) / H]
        report, calls = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "invalid", "prefix")
        self.assertNothingRead(report, calls)

    def test_tampered_file_is_inconclusive(self):
        c = Campaign(self.root, PASS_BIASES)
        np.savez(self.root / "holdout" / "final_render.npz", render=np.zeros((3, H, W), np.float32))
        report, calls = c.evaluate()
        self.assertDecision(report, "inconclusive", "holdout")
        self.assertNothingRead(report, calls)

    def test_nonfinite_render_is_inconclusive(self):
        def mutate(p):
            p["final_render"]["render"][0, 0, 0] = np.inf
        report, calls = self.run_campaign(mutate=_on("control_r1", mutate))
        self.assertDecision(report, "inconclusive", "control_r1")
        self.assertNothingRead(report, calls)

    def test_contract_mismatch_is_invalid(self):
        report, _ = self.run_campaign(
            mutate=_on("holdout", lambda p: p["manifest"].update(num_gaussians_final=319)))
        self.assertDecision(report, "invalid", "holdout")

    def test_contract_type_drift_is_invalid(self):
        report, _ = self.run_campaign(
            mutate=_on("control_r1", lambda p: p["manifest"].update(seed=123.0)))
        self.assertDecision(report, "invalid", "control_r1")

    def test_wrong_fold_counts_is_invalid(self):
        def mutate(p):
            p["manifest"]["fold_counts"]["A"] += 1
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "invalid", "prefix")


class RngTests(AnalyzerBase):
    def test_placeholder_rng_archive_is_inconclusive(self):
        def mutate(p):
            p["rng_before_pool"] = {"k": np.arange(3, dtype=np.uint32)}
        report, calls = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")
        self.assertNothingRead(report, calls)

    def test_numpy_rng_not_advanced_by_pool_is_inconclusive(self):
        def mutate(p):
            p["rng_after_pool"] = copy.deepcopy(p["rng_before_pool"])
        report, calls = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")
        self.assertNothingRead(report, calls)

    def test_wrong_torch_state_size_is_inconclusive(self):
        def mutate(p):
            p["rng_after_pool"]["torch_cpu"] = np.zeros(16, dtype=np.uint8)
        report, calls = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")
        self.assertNothingRead(report, calls)

    def test_all_zero_numpy_key_is_inconclusive(self):
        def mutate(p):
            p["rng_before_pool"]["np_keys"][:] = 0
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")

    def test_python_rng_changed_during_pool_is_inconclusive(self):
        def mutate(p):
            p["rng_after_pool"]["py_internal"][0] ^= 1
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")

    def test_cpu_torch_rng_changed_on_cuda_pool_is_inconclusive(self):
        def mutate(p):
            p["rng_after_pool"]["torch_cpu"][0] ^= 1
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")

    def test_missing_cuda_state_for_device_is_inconclusive(self):
        def mutate(p):
            for key in ("rng_before_pool", "rng_after_pool"):
                del p[key]["cuda_0"]
                p[key]["cuda_count"] = np.asarray(0, dtype=np.int64)
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")

    def test_continuation_rng_differs_from_prefix_is_invalid(self):
        def mutate(p):
            p["rng_continuation_start"]["cuda_0"][0] ^= 1
        report, calls = self.run_campaign(mutate=_on("control_r1", mutate))
        self.assertDecision(report, "invalid", "control_r1")
        self.assertNothingRead(report, calls)

    def test_missing_continuation_rng_is_inconclusive(self):
        report, calls = self.run_campaign(mutate=_on("holdout", lambda p: p.pop("rng_continuation_start")))
        self.assertDecision(report, "inconclusive", "holdout")
        self.assertNothingRead(report, calls)


class InvarianceTests(AnalyzerBase):
    def test_reported_leakage_is_invalid(self):
        report, _ = self.run_campaign(inv_result="failed_leakage")
        self.assertDecision(report, "invalid", "invariance")

    def test_reported_nondeterminism_is_inconclusive(self):
        report, calls = self.run_campaign(inv_result="inconclusive")
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)

    def test_boolean_only_legacy_record_cannot_pass(self):
        def mutate(p):
            m = p["manifest"]
            for key in ("cpu_ab_hash", "trainer_target_hash_by_c", "forward_sha256"):
                del m[key]
            m["checks"] = {k: True for k in LEGACY_CHECK_NAMES}
            for name in INV_FILES:
                del p[name]
        report, calls = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)

    def test_legacy_check_names_with_measurements_are_invalid(self):
        def mutate(p):
            p["manifest"]["checks"] = {k: True for k in LEGACY_CHECK_NAMES}
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_missing_scores_file_is_inconclusive(self):
        report, calls = self.run_campaign(mutate=_on("invariance", lambda p: p.pop("scores")))
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)

    def test_missing_augmented_forward_hashes_is_inconclusive(self):
        def mutate(p):
            del p["manifest"]["forward_sha256"]["augmented"]
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "inconclusive", "invariance")

    def test_true_checks_contradicted_by_scores_are_invalid(self):
        def mutate(p):
            sc = p["scores"]
            sc["scores_cperturb"][sc["selected_cperturb"][0]] += 1.0  # still top-64, bytes differ
        report, calls = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")
        self.assertNothingRead(report, calls)

    def test_true_checks_contradicted_by_forward_hashes_are_invalid(self):
        def mutate(p):
            p["manifest"]["forward_sha256"]["base"]["normal_2"] = "c" * 64
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_passed_claim_with_unstable_augmented_forward_is_invalid(self):
        def mutate(p):
            m = p["manifest"]
            m["forward_sha256"]["augmented"]["cperturb_2"] = "c" * 64
            m["checks"]["augmented_forward_repeat_bitwise_stable"] = False  # honest check
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_pool_recompute_differs_from_saved_is_invalid(self):
        def mutate(p):
            p["pool_recompute_normal"]["feat"][0, 0] += 1.0
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_rng_after_recompute_differs_from_saved_is_invalid(self):
        def mutate(p):
            p["rng_after_pool_recompute_cperturb"]["cuda_0"][1] ^= 1
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_invariance_selection_not_top_k_is_invalid(self):
        def mutate(p):
            sc = p["scores"]
            sc["selected_normal_2"] = sc["selected_normal_2"][::-1].copy()
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")

    def test_invariance_not_bound_to_holdout_selection_is_inconclusive(self):
        def mutate(p):
            sc = p["scores"]
            for r in ("normal_1", "normal_2", "cperturb"):
                sc[f"scores_{r}"] = -sc[f"scores_{r}"]
                sc[f"selected_{r}"] = np.argsort(-sc[f"scores_{r}"], kind="stable")[:64].astype(np.int64)
        report, calls = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)

    def test_invariance_scores_not_bitwise_holdout_scores_is_inconclusive(self):
        def mutate(p):
            for r in ("normal_1", "normal_2", "cperturb"):
                p["scores"][f"scores_{r}"] = p["scores"][f"scores_{r}"] * 2.0  # same order
        report, calls = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "inconclusive", "invariance")
        self.assertNothingRead(report, calls)

    def test_invariance_from_other_implementation_is_invalid(self):
        report, calls = self.run_campaign(
            mutate=_on("invariance", lambda p: p["manifest"].update(pilot_script_sha256="6" * 64)))
        self.assertDecision(report, "invalid", "invariance")
        self.assertNothingRead(report, calls)

    def test_invariance_from_other_prefix_is_invalid(self):
        def mutate(p):
            p["manifest"]["prefix_ref"]["rng_before_pool_hash"] = "0" * 64
        report, _ = self.run_campaign(mutate=_on("invariance", mutate))
        self.assertDecision(report, "invalid", "invariance")


class ProvenanceTests(AnalyzerBase):
    def test_literal_placeholder_trainer_hashes_are_inconclusive(self):
        def mutate(p):
            p["manifest"].update(ab_hash="ab", trainer_target_hash="tt")
        report, calls = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "inconclusive", "prefix")
        self.assertNothingRead(report, calls)

    def test_consistent_but_wrong_ab_hash_is_invalid_before_clean_truth(self):
        report, calls = self.run_campaign(
            mutate=_on("prefix", lambda p: p["manifest"].update(ab_hash="0" * 64)))
        self.assertDecision(report, "invalid", "prefix")
        self.assertTrue(report["noisy_read"])
        self.assertEqual(calls, ["noisy.png"])
        self.assertCleanUnread(report, calls)

    def test_consistent_but_wrong_trainer_target_hash_is_invalid_before_clean_truth(self):
        report, calls = self.run_campaign(
            mutate=_on("prefix", lambda p: p["manifest"].update(trainer_target_hash="0" * 64)))
        self.assertDecision(report, "invalid", "prefix")
        self.assertEqual(calls, ["noisy.png"])
        self.assertCleanUnread(report, calls)

    def test_manifest_input_hash_not_the_verified_noisy_is_invalid(self):
        report, calls = self.run_campaign(
            mutate=_on("holdout", lambda p: p["manifest"].update(input_sha256=an.EXPECTED_NOISY_SHA256)))
        self.assertDecision(report, "invalid", "holdout")
        self.assertNothingRead(report, calls)

    def test_versions_differ_across_artifacts_is_invalid(self):
        def mutate(p):
            p["manifest"]["versions"]["torch"] = "2.5.0"
        report, calls = self.run_campaign(mutate=_on("control_r2", mutate))
        self.assertDecision(report, "invalid", "control_r2")
        self.assertNothingRead(report, calls)

    def test_missing_cuda_versions_is_inconclusive(self):
        def mutate(p):
            del p["manifest"]["versions"]["cuda_device_name"]
        report, _ = self.run_campaign(mutate=_on("control_r1", mutate))
        self.assertDecision(report, "inconclusive", "control_r1")

    def test_implementation_config_drift_is_invalid(self):
        def mutate(p):
            p["manifest"]["implementation_config"]["l1_loss_ratio"] = 0.1
        report, _ = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "invalid", "holdout")

    def test_implementation_config_type_drift_is_invalid(self):
        def mutate(p):
            p["manifest"]["implementation_config"]["eval"] = 0
        report, _ = self.run_campaign(mutate=_on("prefix", mutate))
        self.assertDecision(report, "invalid", "prefix")

    def test_missing_implementation_config_is_inconclusive(self):
        report, _ = self.run_campaign(
            mutate=_on("invariance", lambda p: p["manifest"].pop("implementation_config")))
        self.assertDecision(report, "inconclusive", "invariance")

    def test_fold_helper_mismatch_is_invalid(self):
        report, _ = self.run_campaign(
            mutate=_on("control_r1", lambda p: p["manifest"].update(fold_helper_sha256="7" * 64)))
        self.assertDecision(report, "invalid", "control_r1")

    def test_command_for_other_arm_is_invalid(self):
        def edit(m):
            m["command"] = ["p1817_holdout_birth_pilot.py", "continue", "--arm", "control_r1"]
        report, _ = self.run_campaign(edit_manifest=_on("holdout", edit))
        self.assertDecision(report, "invalid", "holdout")

    def test_missing_contract_document_is_inconclusive(self):
        c = Campaign(self.root, PASS_BIASES)
        with mock.patch.dict(an.CONTRACT_DOCUMENTS, {"amendment_20261105": self.root / "absent.md"}):
            report, calls = c.evaluate()
        self.assertDecision(report, "inconclusive", "contract")
        self.assertNothingRead(report, calls)

    def test_replaced_noisy_file_is_inconclusive_without_decoding(self):
        c = Campaign(self.root, PASS_BIASES)
        Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(c.noisy_path)
        report, calls = c.evaluate()
        self.assertDecision(report, "inconclusive", "noisy")
        self.assertEqual(calls, [])
        self.assertCleanUnread(report, calls)

    def test_noisy_decoded_with_wrong_dtype_is_inconclusive(self):
        c = Campaign(self.root, PASS_BIASES)
        report, calls = c.evaluate(loader=lambda p: an.load_rgb8(p).astype(np.float64))
        self.assertDecision(report, "inconclusive", "noisy")
        self.assertEqual(calls, ["noisy.png"])
        self.assertCleanUnread(report, calls)

    def test_clean_hash_mismatch_is_inconclusive_without_decoding(self):
        report, calls = Campaign(self.root, PASS_BIASES).evaluate(clean_sha="f" * 64)
        self.assertDecision(report, "inconclusive", "clean")
        self.assertEqual(calls, ["noisy.png"])
        self.assertIsNone(report["metrics"])

    def test_trainer_target_hash_ignores_c_and_tracks_a(self):
        img = _decode(Campaign(self.root, PASS_BIASES).noisy_path)
        self.assertEqual(an.trainer_target_sha256(img), _trainer_target_hash(img))
        self.assertEqual(an.trainer_target_sha256(perturb_c_only(img)), an.trainer_target_sha256(img))
        a0 = int(fold_flat_indices(H, W)["A"][0])
        changed = img.copy()
        changed[0, a0 // W, a0 % W] = 1.0 - changed[0, a0 // W, a0 % W]
        self.assertNotEqual(an.trainer_target_sha256(changed), an.trainer_target_sha256(img))


class TimingTests(AnalyzerBase):
    def test_cost_accounting_distinguishes_end_to_end_from_sums(self):
        report, _ = self.run_campaign()
        costs = report["costs"]
        self.assertNotIn("total_actual_campaign_sec", costs)
        self.assertAlmostEqual(costs["actual_campaign_end_to_end_wall_sec"], 51.0)
        # prefix 12 + invariance 3 + arms 4 + 4.5 + 7.5 (prefix counted once).
        self.assertAlmostEqual(costs["sum_of_phase_process_wall_sec"], 31.0)
        self.assertAlmostEqual(costs["inter_phase_gap_sec"], 20.0)
        self.assertEqual(costs["common_prefix_counted_once"]["process_wall_sec"], 12.0)
        self.assertEqual(costs["common_prefix_counted_once"]["compute_sec"]["prefix_wall"], 10.0)
        self.assertEqual(costs["invariance"]["process_wall_sec"], 3.0)
        self.assertEqual(costs["per_arm"]["holdout"]["compute_sec"]["arm_wall"], 6.0)
        self.assertEqual(costs["counterfactual_standalone_cost_sec"],
                         {"control_r1": 16.0, "control_r2": 16.5, "holdout": 19.5})
        self.assertFalse(costs["wall_time_matched"])

    def test_missing_process_wall_is_inconclusive(self):
        report, calls = self.run_campaign(
            mutate=_on("control_r2", lambda p: p["manifest"]["timing_sec"].pop("process_wall")))
        self.assertDecision(report, "inconclusive", "control_r2")
        self.assertNothingRead(report, calls)
        self.assertIsNone(report["costs"])

    def test_missing_process_start_timestamp_is_inconclusive(self):
        report, _ = self.run_campaign(
            mutate=_on("invariance", lambda p: p["manifest"].pop("process_started_unix")))
        self.assertDecision(report, "inconclusive", "invariance")

    def test_timing_not_a_dict_is_inconclusive(self):
        report, _ = self.run_campaign(
            mutate=_on("prefix", lambda p: p["manifest"].update(timing_sec=[1, 2])))
        self.assertDecision(report, "inconclusive", "prefix")

    def test_process_wall_shorter_than_compute_is_inconclusive(self):
        def mutate(p):
            m = p["manifest"]
            m["timing_sec"]["process_wall"] = 5.0
            m["finished_unix"] = m["process_started_unix"] + 5.0
        report, _ = self.run_campaign(mutate=_on("holdout", mutate))
        self.assertDecision(report, "inconclusive", "holdout")

    def test_process_wall_disagreeing_with_timestamps_is_inconclusive(self):
        def mutate(p):
            p["manifest"]["timing_sec"]["process_wall"] = 2.5  # span is 4.0
            p["manifest"]["timing_sec"]["arm_wall"] = 2.5
        report, _ = self.run_campaign(mutate=_on("control_r1", mutate))
        self.assertDecision(report, "inconclusive", "control_r1")

    def test_overlapping_phases_are_inconclusive(self):
        def mutate(p):
            p["manifest"].update(process_started_unix=T0 + 27.0, finished_unix=T0 + 31.5)
        report, calls = self.run_campaign(mutate=_on("control_r2", mutate))
        self.assertDecision(report, "inconclusive", "control_r2")
        self.assertNothingRead(report, calls)


class CliTests(AnalyzerBase):
    def _main(self, c, out, evaluate_fn=None):
        argv = ["--run-root", str(self.root), "--noisy", str(c.noisy_path),
                "--clean", str(c.clean_path), "--out", str(out)]
        real = an.evaluate

        def wrapped(run_root, noisy, clean):
            return real(run_root, noisy, clean, expected_noisy_sha=c.noisy_sha,
                        expected_clean_sha=c.clean_sha)

        with mock.patch.object(an, "evaluate", side_effect=evaluate_fn or wrapped) as ev, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = an.main(argv)
        return code, ev

    def test_refuses_existing_output_before_evaluation(self):
        c = Campaign(self.root, PASS_BIASES)
        out = self.root / "report.json"
        out.write_text("existing")

        def must_not_run(*a):
            raise AssertionError("evaluation must not start")
        code, ev = self._main(c, out, must_not_run)
        self.assertEqual(code, an.EXIT_OUTPUT_REFUSED)
        ev.assert_not_called()
        self.assertEqual(out.read_text(), "existing")

    def test_unwritable_output_is_refused_before_evaluation(self):
        c = Campaign(self.root, PASS_BIASES)
        code, ev = self._main(c, self.root / "no_such_dir" / "report.json")
        self.assertEqual(code, an.EXIT_OUTPUT_REFUSED)
        ev.assert_not_called()

    def test_reserves_output_before_evaluation_and_finalizes_atomically(self):
        c = Campaign(self.root, PASS_BIASES)
        out = self.root / "report.json"
        real = an.evaluate
        seen = {}

        def checking(run_root, noisy, clean):
            seen["reserved"] = json.loads(out.read_text(encoding="utf-8"))
            return real(run_root, noisy, clean, expected_noisy_sha=c.noisy_sha,
                        expected_clean_sha=c.clean_sha)
        code, _ = self._main(c, out, checking)
        self.assertEqual(seen["reserved"]["report_status"], "reserved_incomplete")
        self.assertIsNone(seen["reserved"]["decision"])
        self.assertEqual(code, 0)
        final = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(final["decision"], "preliminary_pass")
        self.assertEqual(final["report_status"], "final")
        self.assertEqual(final["exit_code"], 0)
        self.assertEqual(list(self.root.glob(".report.json.*.tmp")), [])

    def test_exit_codes_per_decision(self):
        c = Campaign(self.root, PASS_BIASES)
        for decision, expected in (("preliminary_pass", 0), ("no_go", 10),
                                   ("inconclusive", 20), ("invalid", 30)):
            out = self.root / f"{decision}.json"
            code, _ = self._main(c, out, lambda *a, d=decision: {"decision": d})
            self.assertEqual(code, expected, decision)
            self.assertEqual(json.loads(out.read_text())["decision"], decision)

    def test_real_inconclusive_campaign_exits_nonzero(self):
        c = Campaign(self.root, PASS_BIASES, skip=("control_r1",))
        out = self.root / "report.json"
        code, _ = self._main(c, out)
        self.assertEqual(code, an.EXIT_CODES["inconclusive"])
        self.assertEqual(json.loads(out.read_text())["decision"], "inconclusive")

    def test_evaluator_crash_writes_error_report(self):
        c = Campaign(self.root, PASS_BIASES)
        out = self.root / "report.json"

        def crash(*a):
            raise RuntimeError("boom")
        code, _ = self._main(c, out, crash)
        self.assertEqual(code, an.EXIT_EVALUATOR_ERROR)
        final = json.loads(out.read_text())
        self.assertEqual(final["decision"], "inconclusive")
        self.assertIn("boom", final["evaluator_error"])

    def test_unknown_decision_is_evaluator_error(self):
        c = Campaign(self.root, PASS_BIASES)
        out = self.root / "report.json"
        code, _ = self._main(c, out, lambda *a: {"decision": "pass"})
        self.assertEqual(code, an.EXIT_EVALUATOR_ERROR)
        self.assertEqual(json.loads(out.read_text())["decision"], "inconclusive")


class StaticTests(unittest.TestCase):
    def test_analyzer_imports_no_torch_or_upstream(self):
        import ast
        tree = ast.parse((SCRIPTS / "analyze_p1817_holdout_birth.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        self.assertTrue(names.isdisjoint({"torch", "model", "gsplat", "utils",
                                          "p1817_holdout_birth_pilot"}), names)

    def test_frozen_config_pins_contract_values(self):
        cfg = an.EXPECTED_IMPLEMENTATION_CONFIG
        self.assertEqual((cfg["l1_loss_ratio"], cfg["l2_loss_ratio"], cfg["ssim_loss_ratio"]),
                         (0.0, 1.0, 0.0))
        self.assertEqual((cfg["gamma"], cfg["init_scale"], cfg["num_gaussians"]), (1.0, 5.0, 320))
        self.assertIs(cfg["disable_color_init"], True)
        self.assertEqual(cfg["init_mode"], "random")
        self.assertEqual((cfg["add_steps"], cfg["add_times"], cfg["max_steps"]), (500, 1, 1000))
        self.assertEqual((cfg["pos_lr"], cfg["scale_lr"], cfg["rot_lr"], cfg["feat_lr"]),
                         (5e-4, 2e-3, 2e-3, 5e-3))
        self.assertIs(cfg["quantize"], False)
        self.assertIs(cfg["disable_tiles"], False)
        self.assertEqual(set(CHECK_NAMES), set(an.INVARIANCE_CHECKS))

    def test_hash_format_and_config_match_pilot(self):
        try:
            import p1817_holdout_birth_pilot as pilot
        except Exception as exc:  # upstream/CUDA deps unavailable
            self.skipTest(f"pilot not importable on this host: {exc!r}")
        arrays = {"b": np.arange(6, dtype=np.float32).reshape(2, 3), "a": np.arange(3)}
        self.assertEqual(pilot.canonical_arrays_hash(arrays), an.canonical_arrays_hash(arrays))
        self.assertEqual(pilot.ARTIFACT_FORMAT, an.ARTIFACT_FORMAT)
        cfg = vars(pilot._build_base_args("prefix", Path("/x/noisy.png"), "cpu",
                                          Path("/x/log"), pilot.PILOT_SEED))
        for key in an.IMPLEMENTATION_CONFIG_EXCLUDED_KEYS:
            cfg.pop(key)
        self.assertEqual(json.dumps(cfg, sort_keys=True),
                         json.dumps(an.EXPECTED_IMPLEMENTATION_CONFIG, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
