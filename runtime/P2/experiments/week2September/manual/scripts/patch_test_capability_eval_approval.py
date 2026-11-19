from pathlib import Path

path = Path("scripts/test_capability_eval.py")
source = path.read_text(encoding="utf-8")

anchor = '''    def test_no_overwrite_of_partial_sidecar(self):
'''

addition = '''    def test_approved_source_clarification_is_accepted(self):
        rows = list(csv.DictReader(
            self.approval_path.open(
                "r", encoding="utf-8-sig", newline=""
            )
        ))

        rows[0]["review_status"] = "APPROVED_WITH_SOURCE_CLARIFICATION"

        with self.approval_path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "problem_id",
                    "review_status",
                    "human_approval",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        self._run_adapter()

        out_dir = self.out_root / self.run_id
        self.assertTrue(
            (out_dir / "student_capability_evaluation_manifest.json").is_file()
        )

    def test_unapproved_review_status_is_rejected(self):
        rows = list(csv.DictReader(
            self.approval_path.open(
                "r", encoding="utf-8-sig", newline=""
            )
        ))

        rows[0]["review_status"] = "PENDING_HUMAN_REVIEW"

        with self.approval_path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "problem_id",
                    "review_status",
                    "human_approval",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaisesRegex(
            ValueError,
            "Gold review status is not approved",
        ):
            self._run_adapter()

'''

if source.count(anchor) != 1:
    raise SystemExit(
        "PATCH_ABORTED: test insertion anchor must occur exactly once; "
        f"found {source.count(anchor)}"
    )

if "test_approved_source_clarification_is_accepted" in source:
    raise SystemExit("PATCH_ABORTED: new tests already exist")

source = source.replace(anchor, addition + anchor, 1)
path.write_text(source, encoding="utf-8")

print("PATCH_PASS: two approval policy tests added")
