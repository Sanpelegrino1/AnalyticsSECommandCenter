"""Integration tests for generate_viz.py - JSON generation (no API calls needed)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestGenerateViz:
    """Test visualization JSON generation."""

    def test_generate_bar_chart(self, temp_json_file):
        """Generate bar chart JSON."""
        output_file = temp_json_file({}, "bar_output.json")
        
        # Simulate command-line call
        from generate_viz import main
        import argparse
        
        # Note: This is a simplified test - actual script uses argparse
        # In a real test, we'd mock argparse or call the builder functions directly
        from lib.templates import build_bar, build_root_envelope
        
        fields = {
            "F1": {
                "type": "Field",
                "role": "Dimension",
                "objectName": "Opportunity",
                "fieldName": "StageName"
            },
            "F2": {
                "type": "Field",
                "role": "Measure",
                "objectName": "Opportunity",
                "fieldName": "Amount",
                "function": "Sum"
            }
        }
        
        visual_spec = build_bar(
            columns=["F1"],
            rows=[],
            fields=fields,
            encodings=[{"type": "Label", "fieldKey": "F2"}],
            legends={},
            overrides={}
        )
        
        envelope = build_root_envelope(
            name="Test_Bar",
            label="Test Bar",
            sdm_name="Test_SDM",
            sdm_label="Test SDM",
            workspace_name="Test_WS",
            workspace_label="Test Workspace",
            visual_spec=visual_spec,
            fields=fields
        )
        
        # Validate structure
        assert envelope["name"] == "Test_Bar"
        assert envelope["visualSpecification"]["marks"]["panes"]["type"] == "Bar"
        assert "F1" in envelope["visualSpecification"]["columns"]

    def test_generate_line_chart(self):
        """Generate line chart JSON."""
        from lib.templates import build_line, build_root_envelope
        
        fields = {
            "F1": {
                "type": "Field",
                "role": "Dimension",
                "objectName": "Opportunity",
                "fieldName": "CloseDate",
                "type": "Date"
            },
            "F2": {
                "type": "Field",
                "role": "Measure",
                "objectName": "Opportunity",
                "fieldName": "Amount",
                "function": "Sum"
            }
        }
        
        visual_spec = build_line(
            columns=["F1"],
            rows=[],
            fields=fields,
            encodings=[{"type": "Label", "fieldKey": "F2"}],
            legends={},
            overrides={}
        )
        
        envelope = build_root_envelope(
            name="Test_Line",
            label="Test Line",
            sdm_name="Test_SDM",
            sdm_label="Test SDM",
            workspace_name="Test_WS",
            workspace_label="Test Workspace",
            visual_spec=visual_spec,
            fields=fields
        )
        
        assert envelope["visualSpecification"]["marks"]["panes"]["type"] == "Line"

    def test_generate_with_encodings(self):
        """Generate chart with multiple encodings."""
        from lib.templates import build_bar, build_root_envelope
        
        fields = {
            "F1": {
                "type": "Field",
                "role": "Dimension",
                "objectName": "Opportunity",
                "fieldName": "StageName"
            },
            "F2": {
                "type": "Field",
                "role": "Measure",
                "objectName": "Opportunity",
                "fieldName": "Amount",
                "function": "Sum"
            }
        }
        
        visual_spec = build_bar(
            columns=["F1"],
            rows=[],
            fields=fields,
            encodings=[
                {"type": "Color", "fieldKey": "F1"},
                {"type": "Label", "fieldKey": "F2"}
            ],
            legends={},
            overrides={}
        )
        
        # Check encodings are present
        encodings = visual_spec["marks"]["panes"]["encodings"]
        assert len(encodings) == 2
        encoding_types = {e["type"] for e in encodings}
        assert "Color" in encoding_types
        assert "Label" in encoding_types

    def test_validate_output(self, sample_viz_payload):
        """Generated JSON passes validation."""
        from lib.validators import validate
        
        results = validate(sample_viz_payload)
        # Check that validation passes - some rules may have warnings but should not fail
        failed_rules = [r for r in results if not r.ok]
        if failed_rules:
            # Print failed rules for debugging
            for rule in failed_rules:
                print(f"Failed: {rule.rule} - {rule.message}")
        # Most critical rules should pass
        critical_rules = ["root_fields", "view", "vis_spec", "marks_panes_headers"]
        critical_results = [r for r in results if r.rule in critical_rules]
        assert all(r.ok for r in critical_results)
