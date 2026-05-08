from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src"

FORBIDDEN_PROJECT_TOPIC_PREFIXES = (
    "/landing_pad/",
    "/mission/",
    "/vehicle/",
)

ALLOWED_EXTERNAL_TOPIC_PREFIXES_BY_PACKAGE = {
    "drone_vehicle": ("/fmu/in/", "/fmu/out/"),
    "drone_perception": ("/camera/",),
}


def _python_files():
    return SOURCE_ROOT.glob("**/*.py")


def _package_name(path):
    relative = path.relative_to(SOURCE_ROOT)
    return relative.parts[0]


def test_project_topics_use_drone_namespace():
    violations = []

    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        for prefix in FORBIDDEN_PROJECT_TOPIC_PREFIXES:
            if prefix in text:
                violations.append(f"{path.relative_to(REPO_ROOT)} uses {prefix}")

    assert not violations, "Project-owned topics must use /drone/...\n" + "\n".join(violations)


def test_external_topics_stay_inside_adapter_packages():
    violations = []

    for path in _python_files():
        package = _package_name(path)
        text = path.read_text(encoding="utf-8")

        for allowed_package, prefixes in ALLOWED_EXTERNAL_TOPIC_PREFIXES_BY_PACKAGE.items():
            if package == allowed_package:
                continue

            for prefix in prefixes:
                if prefix in text:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)} uses external topic {prefix}; "
                        f"expected only in {allowed_package}"
                    )

    assert not violations, "External topics must stay inside adapter packages\n" + "\n".join(violations)

