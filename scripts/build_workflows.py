"""Bundle readable source files into self-contained n8n workflow exports.

Run with --check to detect stale exports without writing anything. The manifest
lists each node's helper files first and its entry script last; n8n needs the
combined script because its Code nodes cannot import our local source files.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "workflow_sources"
EXPORT_ROOT = ROOT / "workflows"


# Example: main()  # python scripts/build_workflows.py --check
def main() -> None:
    """Prepare every export, then either check it or write the changed files."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if exports are stale."
    )
    args = parser.parse_args()
    changes = prepare_exports()
    for path, content in changes:
        if not args.check:
            path.write_text(content, encoding="utf-8")
        print(f"{'Stale' if args.check else 'Updated'}: {path.name}")
    if args.check and changes:
        raise SystemExit(
            "Run python scripts/build_workflows.py to refresh the exports."
        )
    if not changes:
        print("All workflow exports match their sources.")


# Example: changes = prepare_exports()
def prepare_exports() -> list[tuple[Path, str]]:
    """Replace only manifested code/query fields, preserving nodes and connections."""

    manifest = json.loads((SOURCE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    changes = []
    for workflow in manifest:
        path = EXPORT_ROOT / workflow["workflow"]
        original = path.read_text(encoding="utf-8")
        document = json.loads(original)
        for entry in workflow["nodes"]:
            matches = [
                node for node in document["nodes"] if node["name"] == entry["name"]
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one node named {entry['name']!r}.")
            parameters = matches[0]["parameters"]
            if entry["parameter"] not in parameters:
                raise ValueError(f"Missing parameter in node {entry['name']!r}.")
            parameters[entry["parameter"]] = bundle_sources(entry)
        content = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        if content != original:
            changes.append((path, content))
    return changes


# Example: source = bundle_sources(manifest_entry)
def bundle_sources(entry: dict) -> str:
    """Join helper declarations before the entry script; keep SQL as plain text."""

    parts = []
    for name in entry["sources"]:
        source = (SOURCE_ROOT / name).read_text(encoding="utf-8").rstrip()
        if entry["parameter"] == "jsCode":
            source = f"// Source: workflow_sources/{name}\n{source}"
        parts.append(source)
    return "\n\n".join(parts)


if __name__ == "__main__":
    main()
