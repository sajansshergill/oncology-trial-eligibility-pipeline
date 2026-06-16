"""
tests/test_parser.py
--------------------
Unit tests for the Claude API eligibility criteria parser.
Uses mocked API responses so no API key needed for CI.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


MOCK_PARSE_RESPONSE = {
    "inclusion_criteria": [
        {"criterion_id": "IC_001", "type": "ecog",  "field": "ecog_status",
         "operator": "lte", "value": 1, "unit": None, "uln_multiplier": None},
        {"criterion_id": "IC_002", "type": "lab",   "field": "platelet_count",
         "operator": "gte", "value": 100, "unit": "10^9/L", "uln_multiplier": None},
        {"criterion_id": "IC_003", "type": "biomarker", "field": "pdl1_expression",
         "operator": "eq", "value": "high", "unit": None, "uln_multiplier": None},
    ],
    "exclusion_criteria": [
        {"criterion_id": "EC_001", "type": "medication_history", "field": "drug_class",
         "operator": "never_administered", "value": "checkpoint_inhibitor",
         "unit": None, "uln_multiplier": None},
    ]
}


def make_mock_client(response_json: dict):
    mock_content = MagicMock()
    mock_content.text = json.dumps(response_json)
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


class TestParseStructure:

    @patch("eligibility.parser._get_client")
    def test_returns_inclusion_and_exclusion_keys(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(MOCK_PARSE_RESPONSE)
        from eligibility.parser import parse_criteria
        result = parse_criteria("ECOG 0-1. Platelets >= 100. PD-L1 high. No prior immunotherapy.")
        assert "inclusion_criteria" in result
        assert "exclusion_criteria" in result

    @patch("eligibility.parser._get_client")
    def test_inclusion_count(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(MOCK_PARSE_RESPONSE)
        from eligibility.parser import parse_criteria
        result = parse_criteria("sample text")
        assert len(result["inclusion_criteria"]) == 3

    @patch("eligibility.parser._get_client")
    def test_exclusion_count(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(MOCK_PARSE_RESPONSE)
        from eligibility.parser import parse_criteria
        result = parse_criteria("sample text")
        assert len(result["exclusion_criteria"]) == 1

    @patch("eligibility.parser._get_client")
    def test_criterion_has_required_fields(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(MOCK_PARSE_RESPONSE)
        from eligibility.parser import parse_criteria
        result = parse_criteria("sample text")
        for c in result["inclusion_criteria"]:
            assert "criterion_id" in c
            assert "type" in c
            assert "field" in c
            assert "operator" in c

    @patch("eligibility.parser._get_client")
    def test_handles_markdown_fenced_response(self, mock_get_client):
        """Parser should strip ```json fences if model accidentally includes them."""
        fenced = f"```json\n{json.dumps(MOCK_PARSE_RESPONSE)}\n```"
        mock_content = MagicMock()
        mock_content.text = fenced
        mock_msg = MagicMock()
        mock_msg.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_get_client.return_value = mock_client

        from eligibility.parser import parse_criteria
        result = parse_criteria("sample text")
        assert "inclusion_criteria" in result

    @patch("eligibility.parser._get_client")
    def test_missing_keys_get_empty_lists(self, mock_get_client):
        """If API returns partial JSON, missing keys default to empty lists."""
        mock_get_client.return_value = make_mock_client({"inclusion_criteria": []})
        from eligibility.parser import parse_criteria
        result = parse_criteria("sample")
        assert result["exclusion_criteria"] == []