import json
from pathlib import Path


def test_all_case_json_files_are_valid_json():
    paths = sorted(Path("demo-data/cases").glob("*.json"))

    assert len(paths) == 6
    for path in paths:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert parsed["case_id"]
