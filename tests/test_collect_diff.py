import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_FILE = REPO_ROOT / "scripts" / "collect_diff.py"
SPEC = importlib.util.spec_from_file_location("collect_diff", MODULE_FILE)
collect_diff = importlib.util.module_from_spec(SPEC)
sys.modules["collect_diff"] = collect_diff
SPEC.loader.exec_module(collect_diff)

should_include_path = collect_diff.should_include_path
truncate_text = collect_diff.truncate_text


def test_should_include_path_excludes_generated_files():
    assert not should_include_path("src/pkg/__pycache__/thing.pyc")
    assert not should_include_path(".pytest_cache/README.md")
    assert not should_include_path("build/output.txt")
    assert should_include_path("src/drone_vehicle/node.py")


def test_truncate_text_reports_truncation():
    text, truncated = truncate_text("abcdef", 4)

    assert truncated
    assert "truncated" in text


def test_truncate_text_keeps_small_text():
    text, truncated = truncate_text("abc", 10)

    assert text == "abc"
    assert not truncated
