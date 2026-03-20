from __future__ import annotations

import json
from pathlib import Path

from common.contracts import FailureCode, JobStatus

import pipeline
from collector import CollectionPayload
from config import CollectorConfig, CollectionSpec


def test_run_pipeline_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda _path=None: CollectorConfig(
            collections=[CollectionSpec(kind="bookmarks", max_items=10, name="bookmarks")]
        ),
    )

    class FakeCollector:
        def collect(self, spec: CollectionSpec) -> CollectionPayload:
            return CollectionPayload(stage_name=spec.stage_name, items=[{"id": "1"}], warnings=[])

    monkeypatch.setattr(pipeline, "TwitterCliCollector", lambda: FakeCollector())

    result = pipeline.run_pipeline()

    assert result.status == JobStatus.SUCCESS
    assert result.stage("bookmarks") is not None
    assert (tmp_path / "output" / "latest" / "bookmarks.json").exists()
    manifest = json.loads((tmp_path / "output" / "latest" / "manifest.json").read_text())
    assert manifest["run_id"] == result.run_id
    assert manifest["collections"][0]["name"] == "bookmarks"


def test_run_pipeline_partial_on_auth_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda _path=None: CollectorConfig(
            collections=[
                CollectionSpec(kind="bookmarks", max_items=10, name="bookmarks"),
                CollectionSpec(kind="feed", feed_type="for-you", max_items=10, name="home"),
            ]
        ),
    )

    class FakeCollector:
        def collect(self, spec: CollectionSpec) -> CollectionPayload:
            if spec.kind == "bookmarks":
                raise RuntimeError("Cookie expired or invalid (HTTP 401)")
            return CollectionPayload(stage_name=spec.stage_name, items=[{"id": "1"}], warnings=[])

    monkeypatch.setattr(pipeline, "TwitterCliCollector", lambda: FakeCollector())

    result = pipeline.run_pipeline()

    assert result.status == JobStatus.PARTIAL
    assert result.failure_code == FailureCode.AUTH_FAILED
    assert result.stage("bookmarks").failure_code == FailureCode.AUTH_FAILED
    manifest = json.loads((tmp_path / "output" / "latest" / "manifest.json").read_text())
    assert manifest["collections"][0]["name"] == "home"


def test_run_pipeline_writes_post_actions_artifact(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda _path=None: CollectorConfig(
            collections=[
                CollectionSpec(
                    kind="bookmarks",
                    max_items=10,
                    name="bookmarks",
                    remove_after_collect=True,
                )
            ]
        ),
    )

    class FakeCollector:
        def collect(self, spec: CollectionSpec) -> CollectionPayload:
            return CollectionPayload(
                stage_name=spec.stage_name,
                items=[{"id": "1"}],
                warnings=[],
            )

        def remove_bookmarks(self, tweet_ids: list[str]) -> dict[str, object]:
            assert tweet_ids == ["1"]
            return {
                "remove_after_collect": True,
                "removed_count": 1,
                "removed_ids": ["1"],
                "failed_count": 0,
                "failed": [],
            }

    monkeypatch.setattr(pipeline, "TwitterCliCollector", lambda: FakeCollector())

    result = pipeline.run_pipeline()

    stage = result.stage("bookmarks")
    assert stage is not None
    assert "remove_after_collect enabled; unbookmarked=1" in stage.warnings
    post_actions_path = tmp_path / "artifacts" / "twitter-collector" / result.run_id / "bookmarks" / "post-actions.json"
    assert post_actions_path.exists()
    post_actions = json.loads(post_actions_path.read_text())
    assert post_actions["removed_ids"] == ["1"]


def test_run_pipeline_writes_like_cleanup_artifact(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda _path=None: CollectorConfig(
            collections=[
                CollectionSpec(
                    kind="likes",
                    max_items=10,
                    name="likes",
                    remove_after_collect=True,
                )
            ]
        ),
    )

    class FakeCollector:
        def collect(self, spec: CollectionSpec) -> CollectionPayload:
            return CollectionPayload(
                stage_name=spec.stage_name,
                items=[{"id": "9"}],
                warnings=[],
            )

        def remove_likes(self, tweet_ids: list[str]) -> dict[str, object]:
            assert tweet_ids == ["9"]
            return {
                "remove_after_collect": True,
                "action": "unlike",
                "removed_count": 1,
                "removed_ids": ["9"],
                "failed_count": 0,
                "failed": [],
            }

    monkeypatch.setattr(pipeline, "TwitterCliCollector", lambda: FakeCollector())

    result = pipeline.run_pipeline()

    stage = result.stage("likes")
    assert stage is not None
    assert "remove_after_collect enabled; unliked=1" in stage.warnings
    post_actions_path = tmp_path / "artifacts" / "twitter-collector" / result.run_id / "likes" / "post-actions.json"
    assert post_actions_path.exists()
    post_actions = json.loads(post_actions_path.read_text())
    assert post_actions["action"] == "unlike"
