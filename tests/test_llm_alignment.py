"""Tests for LLM-assisted alignment verification and repair patch validation."""
import json
import tempfile
import unittest
from pathlib import Path

import tests  # noqa: F401
from hanviet.alignment.llm_review.applier import apply_approved_alignment_repairs
from hanviet.alignment.llm_review.patch_validator import validate_alignment_proposals
from hanviet.alignment.llm_review.verifier import run_llm_alignment_verification
from hanviet.common.llm_client import LLMClient, LLMConfig


def _sample_draft():
    return {
        "work": "CPO_11/bai0024/TV04",
        "fingerprint": "fp_abc123",
        "units": {
            "han": [
                {"id": "CPO_11/bai0024/TV04/han/0001", "text": "弟二中"},
                {"id": "CPO_11/bai0024/TV04/han/0002", "text": "阮尚賢"},
            ],
            "am": [
                {"id": "CPO_11/bai0024/TV04/am/0001", "text": "Đệ nhị trung"},
                {"id": "CPO_11/bai0024/TV04/am/0002", "text": "Nguyễn Thượng Hiền"},
            ],
            "nghia": [
                {"id": "CPO_11/bai0024/TV04/nghia/0001", "text": "Đệ nhị giáp tiến sĩ Nguyễn Thượng Hiền"},
            ],
            "tho": [],
        },
        "links": {
            "am": [
                {"han_ids": ["CPO_11/bai0024/TV04/han/0001"], "am_ids": ["CPO_11/bai0024/TV04/am/0001"]},
                {"han_ids": ["CPO_11/bai0024/TV04/han/0002"], "am_ids": ["CPO_11/bai0024/TV04/am/0002"]},
            ],
            "nghia": [
                {"han_ids": ["CPO_11/bai0024/TV04/han/0001"], "nghia_ids": ["CPO_11/bai0024/TV04/nghia/0001"]}
            ],
            "tho": [],
        },
        "unmatched": {"han": ["CPO_11/bai0024/TV04/han/0002"], "am": [], "nghia": [], "tho": []},
        "rows": [],
    }


class TestLLMAlignmentVerification(unittest.TestCase):
    def test_unconfigured_llm_writes_before_and_returns_not_run(self):
        draft = _sample_draft()
        with tempfile.TemporaryDirectory() as tmp:
            stage_dir = Path(tmp) / "06_llm_hau_kiem"
            res = run_llm_alignment_verification(
                draft, llm_config=LLMConfig(provider=None, model=None), stage_dir=stage_dir
            )
            self.assertEqual(res["status"], "LLM_NOT_RUN")
            self.assertTrue((stage_dir / "before" / "draft_snapshot.json").is_file())
            self.assertTrue((stage_dir / "requests" / "verification_request.json").is_file())

    def test_malformed_json_does_not_pass_schema(self):
        draft = _sample_draft()
        client = LLMClient(
            LLMConfig(provider="mock", model="m1", max_retries=0),
            transport=lambda *_: ("not json at all", {}),
        )
        res = run_llm_alignment_verification(draft, llm_config=client.config, client=client)
        self.assertEqual(res["status"], "SCHEMA_ERROR")

    def test_validator_guards_and_manual_repair_application(self):
        draft = _sample_draft()
        good_resp = {
            "work": draft["work"],
            "fingerprint": draft["fingerprint"],
            "findings": [{
                "target_kind": "nghia",
                "formal_error": "OMISSION",
                "diagnostic_labels": ["BOUNDARY_ERROR"],
                "han_ids": ["CPO_11/bai0024/TV04/han/0001", "CPO_11/bai0024/TV04/han/0002"],
                "target_ids": ["CPO_11/bai0024/TV04/nghia/0001"],
                "reason": "nghia/0001 includes both han/0001 and han/0002",
            }],
            "proposals": [
                {
                    "proposal_id": "p1",
                    "target_kind": "nghia",
                    "operation": "MERGE",
                    "han_ids": ["CPO_11/bai0024/TV04/han/0001", "CPO_11/bai0024/TV04/han/0002"],
                    "target_ids": ["CPO_11/bai0024/TV04/nghia/0001"],
                    "reason": "Include han/0002 in the aligned nghia span",
                    "status": "PROPOSED",
                },
                # Bad proposal trying to fabricate translation and use nonexistent ID
                {
                    "proposal_id": "p_bad",
                    "target_kind": "tho",
                    "operation": "ADD_LINK",
                    "han_ids": ["CPO_11/bai0024/TV04/han/9999"],
                    "target_ids": ["CPO_11/bai0024/TV04/tho/0001"],
                    "fabricated_translation": "Fake poem",
                    "reason": "invalid",
                    "status": "PROPOSED",
                },
            ],
        }
        # Cannot overwrite approved review
        locked = validate_alignment_proposals(draft, good_resp, existing_review={"approved": True})
        self.assertTrue(locked["locked_by_approved_review"])
        self.assertEqual(len(locked["valid_proposals"]), 0)

        validated = validate_alignment_proposals(draft, good_resp, existing_review=None)
        self.assertEqual(len(validated["valid_proposals"]), 1)
        self.assertEqual(len(validated["rejected_proposals"]), 1)

        with tempfile.TemporaryDirectory() as tmp:
            stage_dir = Path(tmp) / "06_llm_hau_kiem"
            (stage_dir / "patches").mkdir(parents=True)
            (stage_dir / "manual_review").mkdir(parents=True)
            (stage_dir / "after").mkdir(parents=True)
            applied = apply_approved_alignment_repairs(
                draft, validated, {"p1": "APPROVE"}, stage_dir=stage_dir
            )
            self.assertFalse(applied["candidate_review"]["approved"])
            self.assertEqual(applied["unmatched"]["han"], [])
            self.assertEqual(
                applied["candidate_review"]["links"]["nghia"][0]["han_ids"],
                ["CPO_11/bai0024/TV04/han/0001", "CPO_11/bai0024/TV04/han/0002"],
            )


if __name__ == "__main__":
    unittest.main()
