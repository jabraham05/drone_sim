#!/usr/bin/env python3
"""Run OpenAI-backed code reviews for GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-nano"

REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["none", "low", "medium", "high", "critical"]},
        "blocking": {"type": "boolean"},
        "docs_required": {"type": "boolean"},
        "tests_required": {"type": "boolean"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "file": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": ["severity", "title", "description", "file", "recommendation"],
            },
        },
        "suggested_next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "risk_level",
        "blocking",
        "docs_required",
        "tests_required",
        "findings",
        "suggested_next_steps",
    ],
}


@dataclass(frozen=True)
class ReviewResult:
    summary: str
    risk_level: str
    blocking: bool
    docs_required: bool
    tests_required: bool
    findings: list[dict[str, Any]]
    suggested_next_steps: list[str]


def load_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_prompt(mode: str, diff_text: str, static_report: str) -> str:
    focus = (
        "Lightweight review for correctness, maintainability, docs drift, and obvious ROS/PX4 risks."
        if mode == "push"
        else "Deep PR review for safety, security, robotics risks, CI risks, and docs/test gaps."
    )
    return f"""You are reviewing an autonomous drone delivery simulation repository.

Review mode: {mode}
Review focus: {focus}

Project rules:
- Project-owned ROS topics must use /drone/... and topic constants from drone_common.topics.
- PX4 /fmu/... topics must stay isolated to drone_vehicle.
- Raw camera /camera/... topics must stay isolated to drone_perception.
- Code changes are incomplete unless affected docs and suggested next steps are updated.
- For drone safety, prioritize fail-safe behavior, emergency-stop behavior, and avoiding unsafe PX4 command patterns.

Static tool output:
{static_report or "[none provided]"}

Git diff:
{diff_text or "[empty diff]"}

Return only JSON matching the requested schema. Mark blocking=true only for critical safety or security issues.
"""


def call_openai(api_key: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "code_review",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc


def extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def parse_review_json(text: str) -> ReviewResult:
    data = json.loads(text)
    return ReviewResult(
        summary=data["summary"],
        risk_level=data["risk_level"],
        blocking=bool(data["blocking"]),
        docs_required=bool(data["docs_required"]),
        tests_required=bool(data["tests_required"]),
        findings=list(data["findings"]),
        suggested_next_steps=list(data["suggested_next_steps"]),
    )


def should_block_review(review: ReviewResult, fail_on_critical: bool) -> bool:
    if not fail_on_critical:
        return False
    return review.blocking and any(finding.get("severity") == "critical" for finding in review.findings)


def render_markdown(review: ReviewResult, mode: str, model: str) -> str:
    lines = [
        f"## OpenAI {mode.title()} Code Review",
        "",
        f"- Model: `{model}`",
        f"- Risk level: `{review.risk_level}`",
        f"- Blocking: `{str(review.blocking).lower()}`",
        f"- Docs required: `{str(review.docs_required).lower()}`",
        f"- Tests required: `{str(review.tests_required).lower()}`",
        "",
        "### Summary",
        "",
        review.summary,
        "",
        "### Findings",
        "",
    ]

    if not review.findings:
        lines.append("No findings.")
    else:
        for finding in review.findings:
            lines.extend(
                [
                    f"- **{finding['severity'].upper()}** `{finding['file']}`: {finding['title']}",
                    f"  - {finding['description']}",
                    f"  - Recommendation: {finding['recommendation']}",
                ]
            )

    lines.extend(["", "### Suggested Next Steps", ""])
    if review.suggested_next_steps:
        lines.extend(f"{index}. {step}" for index, step in enumerate(review.suggested_next_steps, start=1))
    else:
        lines.append("No suggested next steps.")
    lines.append("")
    return "\n".join(lines)


def skipped_markdown(reason: str, mode: str) -> str:
    return f"## OpenAI {mode.title()} Code Review\n\nSkipped: {reason}\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenAI code review.")
    parser.add_argument("--mode", choices=("push", "pr"), required=True)
    parser.add_argument("--diff-file", type=Path, required=True)
    parser.add_argument("--static-report", type=Path)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--fail-on-critical", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_REVIEW_MODEL", DEFAULT_MODEL)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        args.output_md.write_text(skipped_markdown("OPENAI_API_KEY is not configured.", args.mode), encoding="utf-8")
        return 0

    diff_text = load_text(args.diff_file)
    static_report = load_text(args.static_report)
    prompt = build_prompt(args.mode, diff_text, static_report)

    response = call_openai(api_key, model, prompt)
    review = parse_review_json(extract_output_text(response))
    markdown = render_markdown(review, args.mode, model)
    args.output_md.write_text(markdown, encoding="utf-8")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(response, indent=2), encoding="utf-8")

    return 1 if should_block_review(review, args.fail_on_critical) else 0


if __name__ == "__main__":
    raise SystemExit(main())

