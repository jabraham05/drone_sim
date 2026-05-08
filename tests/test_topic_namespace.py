import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src"
TOPIC_CONSTANTS_FILE = SOURCE_ROOT / "drone_common" / "drone_common" / "topics.py"

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


def _source_python_files():
    for path in _python_files():
        if "test" in path.relative_to(SOURCE_ROOT).parts:
            continue
        yield path


def _package_name(path):
    relative = path.relative_to(SOURCE_ROOT)
    return relative.parts[0]


def _string_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def test_project_topics_use_drone_namespace():
    violations = []

    for path in _source_python_files():
        if path == TOPIC_CONSTANTS_FILE:
            continue

        for value in _string_literals(path):
            for prefix in FORBIDDEN_PROJECT_TOPIC_PREFIXES:
                if value.startswith(prefix):
                    violations.append(f"{path.relative_to(REPO_ROOT)} uses {value}")

    assert not violations, "Project-owned topics must use /drone/...\n" + "\n".join(violations)


def test_external_topics_stay_inside_adapter_packages():
    violations = []

    for path in _source_python_files():
        if path == TOPIC_CONSTANTS_FILE:
            continue

        package = _package_name(path)

        for allowed_package, prefixes in ALLOWED_EXTERNAL_TOPIC_PREFIXES_BY_PACKAGE.items():
            if package == allowed_package:
                continue

            for value in _string_literals(path):
                for prefix in prefixes:
                    if value.startswith(prefix):
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)} uses external topic {value}; "
                            f"expected only in {allowed_package}"
                        )

    assert not violations, "External topics must stay inside adapter packages\n" + "\n".join(violations)


def test_topic_literals_are_defined_in_common_topics():
    topic_fragments = (
        "/drone/",
        "/fmu/in/",
        "/fmu/out/",
        "/camera/",
    )
    violations = []

    for path in _source_python_files():
        if path == TOPIC_CONSTANTS_FILE:
            continue

        for value in _string_literals(path):
            for fragment in topic_fragments:
                if value.startswith(fragment):
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)} contains {value}; "
                        "import topic names from drone_common.topics instead"
                    )

    assert not violations, "Topic literals must be centralized in drone_common.topics\n" + "\n".join(violations)
