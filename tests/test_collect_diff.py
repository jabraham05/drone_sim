from scripts.collect_diff import should_include_path, truncate_text


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

