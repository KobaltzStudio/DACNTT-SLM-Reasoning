from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "p1p2_method_registry.yaml"


class MethodRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            cls.registry = yaml.safe_load(handle)

    def test_registry_schema_and_version(self):
        self.assertEqual(self.registry["schema_version"], "p1p2.method-registry.v1")
        self.assertEqual(self.registry["registry_version"], 1)

    def test_registered_seeds_are_frozen(self):
        self.assertEqual(self.registry["registered_seeds"], [13, 42, 2026])

    def test_required_methods_exist(self):
        required = {"B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2", "P1-GRAPH"}
        self.assertTrue(required.issubset(self.registry["methods"]))

    def test_p2_methods_delegate_to_frozen_config(self):
        for method in ("B2", "B3", "B4", "B5"):
            entry = self.registry["methods"][method]
            self.assertEqual(entry["implementation"], "existing_p2")
            self.assertEqual(entry["source_config"], "config/experiment_config.json")

    def test_b4_b5_nll_policies_are_distinct_and_explicit(self):
        methods = self.registry["methods"]
        self.assertEqual(methods["B4"]["nll_checkpoint_policy"], "S0")
        self.assertEqual(methods["B5"]["nll_checkpoint_policy"], "current_checkpoint")

    def test_p1_deficit_does_not_require_nll_or_graph(self):
        entry = self.registry["methods"]["P1-DEFICIT"]
        self.assertTrue(entry["requires_capability_state"])
        self.assertFalse(entry["requires_nll"])
        self.assertFalse(entry["graph_evidence_required"])

    def test_p1p2_policy_is_frozen_at_alpha_half(self):
        policy = self.registry["methods"]["P1P2"]["priority_policy"]
        self.assertEqual(policy["policy_id"], "p1p2_alpha_050_v1")
        self.assertEqual(policy["alpha"], 0.5)
        self.assertFalse(policy["alpha_tuned"])
        self.assertEqual(
            policy["formula"],
            "alpha * p1_deficit + (1 - alpha) * percentile_rank_l_proxy",
        )

    def test_p1_graph_is_disabled_without_evidence(self):
        entry = self.registry["methods"]["P1-GRAPH"]
        self.assertFalse(entry["enabled"])
        self.assertTrue(entry["graph_evidence_required"])
        self.assertGreaterEqual(len(entry["enablement_requirements"]), 4)

    def test_round_mapping_and_dev_only_evaluation(self):
        protocol = self.registry["checkpoint_protocol"]
        self.assertEqual(protocol["baseline"], "S0")
        self.assertEqual(protocol["rounds"], {1: "S1", 2: "S2", 3: "S3"})
        self.assertEqual(protocol["p2_round_index_offset"], -1)
        self.assertEqual(protocol["evaluation_split"], "dev")
        self.assertFalse(protocol["test_evaluation_during_rounds"])

    def test_custom_seed_namespace_is_separate(self):
        custom = self.registry["custom_seed_policy"]
        self.assertTrue(custom["enabled"])
        self.assertEqual(custom["registered_namespace"], "p1p2_integration")
        self.assertEqual(custom["custom_namespace"], "p1p2_integration_custom")

    def test_forbidden_namespace_is_runs_main(self):
        self.assertIn("runs/main", self.registry["output_namespaces"]["forbidden"])


if __name__ == "__main__":
    unittest.main()
