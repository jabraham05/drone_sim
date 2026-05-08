import importlib.util
from pathlib import Path


TOPICS_FILE = Path(__file__).resolve().parents[1] / "drone_common" / "topics.py"
SPEC = importlib.util.spec_from_file_location("topics", TOPICS_FILE)
topics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(topics)


def test_project_topics_use_drone_namespace():
    for topic in topics.PROJECT_TOPICS:
        assert topic.startswith("/drone/")


def test_topic_groups_are_unique():
    all_topics = topics.PROJECT_TOPICS + topics.PX4_TOPICS + topics.CAMERA_TOPICS
    assert len(all_topics) == len(set(all_topics))


def test_adapter_topics_are_grouped_separately():
    for topic in topics.PX4_TOPICS:
        assert topic.startswith("/fmu/")

    for topic in topics.CAMERA_TOPICS:
        assert topic.startswith("/camera/")
