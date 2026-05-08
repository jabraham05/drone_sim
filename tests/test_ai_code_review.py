import json

from scripts.ai_code_review import (
    ReviewResult,
    build_prompt,
    parse_review_json,
    render_markdown,
    should_block_review,
)


def test_parse_review_json():
    review = parse_review_json(
        json.dumps(
            {
                "summary": "Looks good.",
                "risk_level": "low",
                "blocking": False,
                "docs_required": True,
                "tests_required": False,
                "findings": [],
                "suggested_next_steps": ["Update docs."],
            }
        )
    )

    assert review.summary == "Looks good."
    assert review.docs_required
    assert review.suggested_next_steps == ["Update docs."]


def test_should_block_only_critical_when_enabled():
    review = ReviewResult(
        summary="Critical issue.",
        risk_level="critical",
        blocking=True,
        docs_required=False,
        tests_required=True,
        findings=[
            {
                "severity": "critical",
                "title": "Unsafe command",
                "description": "PX4 command bypasses safety.",
                "file": "src/example.py",
                "recommendation": "Route through safety layer.",
            }
        ],
        suggested_next_steps=[],
    )

    assert should_block_review(review, fail_on_critical=True)
    assert not should_block_review(review, fail_on_critical=False)


def test_render_markdown_includes_findings():
    review = ReviewResult(
        summary="Review summary.",
        risk_level="medium",
        blocking=False,
        docs_required=True,
        tests_required=True,
        findings=[
            {
                "severity": "medium",
                "title": "Missing test",
                "description": "No test covers the change.",
                "file": "tests/example.py",
                "recommendation": "Add coverage.",
            }
        ],
        suggested_next_steps=["Add test."],
    )

    markdown = render_markdown(review, "pr", "gpt-5-nano")

    assert "OpenAI Pr Code Review" in markdown
    assert "Missing test" in markdown
    assert "Add test." in markdown


def test_prompt_mentions_drone_safety_rules():
    prompt = build_prompt("pr", "diff", "bandit report")

    assert "/drone/..." in prompt
    assert "PX4" in prompt
    assert "bandit report" in prompt

