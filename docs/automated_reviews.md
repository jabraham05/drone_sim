# Automated Reviews

This project uses GitHub Actions for normal CI plus optional OpenAI-backed code reviews.

## Required Secret

Add this repository secret in GitHub:

```text
OPENAI_API_KEY
```

The workflows skip OpenAI review cleanly if the secret is not configured.

## Optional Repository Variables

```text
OPENAI_REVIEW_MODEL
AI_REVIEW_MAX_DIFF_CHARS
```

Defaults:

- `OPENAI_REVIEW_MODEL`: `gpt-5-nano`
- `AI_REVIEW_MAX_DIFF_CHARS`: `60000`

## Push Review

Workflow:

```text
.github/workflows/ai_push_review.yml
```

Behavior:

- Runs on every push.
- Collects the pushed diff.
- Sends the bounded diff to the OpenAI Responses API.
- Writes the review to the GitHub Actions job summary.
- Does not block pushes for review findings.

The push review is intended to catch early correctness, documentation, topic-contract, and maintainability issues.

## PR Safety And Security Review

Workflow:

```text
.github/workflows/ai_pr_safety_review.yml
```

Behavior:

- Runs on internal pull requests.
- Skips fork PRs to protect repository secrets.
- Runs lightweight validation with `compileall` and `pytest`.
- Runs `bandit` and `pip-audit`.
- Sends the PR diff and static-tool output to the OpenAI Responses API.
- Posts a new PR comment on every run.
- Blocks the PR only when OpenAI returns a critical blocking finding.

The PR review focuses on:

- Python security issues
- unsafe GitHub Actions or shell patterns
- leaked secrets
- ROS topic contract violations
- unsafe PX4 command patterns
- drone safety and failsafe risks
- missing tests or documentation

## Local Script Usage

Collect a diff:

```bash
python3 scripts/collect_diff.py \
  --base main \
  --head HEAD \
  --output ai-review/diff.patch
```

Run a review locally:

```bash
OPENAI_API_KEY=... python3 scripts/ai_code_review.py \
  --mode pr \
  --diff-file ai-review/diff.patch \
  --output-md ai-review/review.md \
  --fail-on-critical
```

## Output Format

The OpenAI review asks for structured JSON with:

- `summary`
- `risk_level`
- `blocking`
- `docs_required`
- `tests_required`
- `findings`
- `suggested_next_steps`

The script converts that JSON into Markdown for GitHub summaries and PR comments.

## Safety Policy

- Push reviews are advisory only.
- PR reviews block only critical safety or security findings.
- Static tools remain the first deterministic security layer.
- AI review output should be treated as engineering feedback, not as a replacement for human review.

## Suggested Next Steps

1. Add `OPENAI_API_KEY` as a GitHub repository secret.
2. Optionally set `OPENAI_REVIEW_MODEL` if the default model should change.
3. Open a small internal PR to verify the PR comment and blocking behavior.
4. Tune prompts and thresholds after the first few reviews.

