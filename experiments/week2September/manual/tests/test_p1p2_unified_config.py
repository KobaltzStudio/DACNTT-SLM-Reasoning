\
import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "p1p2_unified_run.yaml"
REGISTRY_PATH = ROOT / "config" / "p1p2_method_registry.yaml"
P2_CONFIG_PATH = ROOT / "config" / "experiment_config.json"


class UnifiedRunConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            cls.config = yaml.safe_load(handle)
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            cls.registry = yaml.safe_load(handle)
        with P2_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            cls.p2 = json.load(handle)

    def test_schema_and_version(self):
        self.assertEqual(self.config["schema_version"], "p1p2.unified-run.v1")
        self.assertEqual(self.config["config_version"], 1)

    def test_registered_seeds_match_registry(self):
        self.assertEqual(
            self.config["execution"]["default_seeds"],
            self.registry["registered_seeds"],
        )

    def test_default_methods_are_registered_and_enabled(self):
        methods = self.config["execution"]["default_methods"]
        for method in methods:
            self.assertIn(method, self.registry["methods"])
            self.assertTrue(self.registry["methods"][method]["enabled"])

    def test_round_and_checkpoint_mapping(self):
        rounds = self.config["execution"]["rounds"]
        self.assertEqual(rounds["checkpoint_by_round"][0], "S0")
        self.assertEqual(rounds["checkpoint_by_round"][1], "S1")
        self.assertEqual(rounds["checkpoint_by_round"][2], "S2")
        self.assertEqual(rounds["checkpoint_by_round"][3], "S3")
        self.assertEqual(rounds["p2_round_index_offset"], -1)

    def test_model_revisions_match_frozen_p2_config(self):
        models = self.config["models"]
        self.assertEqual(models["teacher"]["model_id"], self.p2["teacher"]["model"])
        self.assertEqual(models["teacher"]["revision"], self.p2["teacher"]["revision"])
        self.assertEqual(models["student"]["model_id"], self.p2["student"]["model"])
        self.assertEqual(models["student"]["revision"], self.p2["student"]["revision"])

    def test_budget_and_selector_constants_match_p2(self):
        selection = self.config["selection"]
        self.assertEqual(selection["budget"]["beta_round_tokens"], self.p2["budget"]["beta_round_tokens"])
        self.assertEqual(selection["budget"]["beta_total_tokens"], self.p2["budget"]["beta_total_tokens"])
        self.assertEqual(selection["n_cap"], self.p2["selection"]["n_cap"])
        self.assertEqual(selection["tie_break"], self.p2["selection"]["tie_break"])
        self.assertEqual(selection["allow_reselect_across_rounds"], self.p2["selection"]["allow_reselect_across_rounds"])

    def test_p1p2_alpha_is_frozen(self):
        policy = self.config["selection"]["p1p2_priority"]
        self.assertEqual(policy["alpha"], 0.5)
        self.assertFalse(policy["alpha_tuned"])
        self.assertEqual(self.p2["selection"]["alpha"], 0.5)
        self.assertFalse(self.p2["selection"]["alpha_tuned"])

    def test_nll_policies_match_registry(self):
        runtime = self.config["method_runtime"]
        registry_methods = self.registry["methods"]
        for method in ("B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2"):
            expected = registry_methods[method].get("nll_checkpoint_policy", "none")
            self.assertEqual(runtime[method]["nll_policy"], expected)

    def test_dev_and_test_protocol(self):
        data = self.config["data"]
        self.assertEqual(data["dev"]["expected_count"], 500)
        self.assertEqual(data["dev_select"]["expected_count"], 415)
        self.assertEqual(data["dev_graph"]["expected_count"], 85)
        self.assertFalse(data["test"]["allowed_during_training_rounds"])
        self.assertFalse(data["test"]["allowed_for_checkpoint_selection_or_tuning"])
        self.assertEqual(self.config["round_protocol"]["evaluation_split"], "dev")
        self.assertFalse(self.config["round_protocol"]["checkpoint_selection"]["d_test_allowed"])

    def test_graph_method_remains_disabled(self):
        self.assertFalse(self.config["selection"]["p1_graph"]["enabled"])
        self.assertFalse(self.config["method_runtime"]["P1-GRAPH"]["enabled"])
        self.assertFalse(self.registry["methods"]["P1-GRAPH"]["enabled"])

    def test_namespace_separation_and_protected_paths(self):
        artifacts = self.config["artifacts"]
        self.assertEqual(artifacts["registered"]["runs_root"], self.registry["output_namespaces"]["registered"]["runs"])
        self.assertEqual(artifacts["custom"]["runs_root"], self.registry["output_namespaces"]["custom"]["runs"])
        self.assertIn("runs/main", artifacts["forbidden_write_roots"])
        self.assertIn("runs/main", self.registry["output_namespaces"]["forbidden"])

    def test_post_eval_cli_contract(self):
        hook = self.config["post_evaluation_hook"]
        required = {"method", "seed", "round", "prediction", "checkpoint", "output_dir"}
        self.assertEqual(set(hook["required_cli_inputs"]), required)
        self.assertEqual(hook["supported_round_values"], [0, 1, 2, 3])
        self.assertFalse(hook["p1_graph_allowed"])

    def test_pool_fingerprint_and_verified_filter(self):
        pool = self.config["data"]["verified_pool"]
        self.assertEqual(pool["expected_records"], 4353)
        self.assertEqual(pool["expected_sha256"], "95f34cff848bfbd16305e5f0ecc2656525dc1e319ca2b1a404f9b75c8029cd04")
        self.assertEqual(pool["required_verification_status"], "valid")

    def test_training_parameters_are_not_duplicated(self):
        training = self.config["training"]
        self.assertEqual(training["configuration_source"], "config/experiment_config.json")
        self.assertTrue(training["do_not_duplicate_hyperparameters"])

    def test_dry_run_and_resume_safety(self):
        execution = self.config["execution"]
        self.assertTrue(execution["dry_run"]["must_not_train"])
        self.assertTrue(execution["dry_run"]["must_not_write_model_checkpoints"])
        self.assertTrue(execution["resume"]["require_valid_parent_checkpoint"])
        self.assertTrue(execution["resume"]["never_overwrite_completed_round"])


if __name__ == "__main__":
    unittest.main()
