"""Make the relationship between readable scripts and exported workflows testable."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_workflows


# Example: python -m unittest tests.test_workflow_build
class WorkflowBuildTests(unittest.TestCase):
    """Source changes must be reproducible without touching workflow settings."""

    # Example: self.test_repository_exports_are_current()
    def test_repository_exports_are_current(self):
        """Every committed export already contains the current bundled source."""

        self.assertEqual(build_workflows.prepare_exports(), [])

    # Example: self.test_build_preserves_workflow_settings_and_is_repeatable()
    def test_build_preserves_workflow_settings_and_is_repeatable(self):
        """Refreshing script text preserves node IDs, credentials, and connections."""

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            (source / "main.js").write_text("return [];\n", encoding="utf-8")
            (source / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "workflow": "example.json",
                            "nodes": [
                                {
                                    "name": "Example",
                                    "parameter": "jsCode",
                                    "sources": ["main.js"],
                                }
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            document = {
                "active": False,
                "connections": {"Example": {}},
                "nodes": [
                    {
                        "id": "keep-me",
                        "name": "Example",
                        "credentials": {"reference": "keep-me"},
                        "parameters": {"jsCode": "old", "other": True},
                    }
                ],
            }
            target = root / "example.json"
            target.write_text(json.dumps(document), encoding="utf-8")
            with patch.object(build_workflows, "SOURCE_ROOT", source):
                with patch.object(build_workflows, "EXPORT_ROOT", root):
                    changes = build_workflows.prepare_exports()
                    self.assertEqual(len(changes), 1)
                    path, content = changes[0]
                    updated = json.loads(content)
                    document["nodes"][0]["parameters"]["jsCode"] = updated["nodes"][0][
                        "parameters"
                    ]["jsCode"]
                    self.assertEqual(updated, document)
                    path.write_text(content, encoding="utf-8")
                    self.assertEqual(build_workflows.prepare_exports(), [])
