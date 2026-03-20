"""Configuration loading for twitter-collector."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "collections.yaml"


CollectionKind = Literal["feed", "bookmarks", "likes", "user-posts"]
FeedType = Literal["for-you", "following"]


class CollectionSpec(BaseModel):
    name: str | None = None
    kind: CollectionKind
    max_items: int = Field(default=50, ge=1, le=1000)
    feed_type: FeedType | None = None
    target: str | None = None
    filter_enabled: bool = False
    remove_after_collect: bool = False

    @model_validator(mode="after")
    def _validate(self) -> "CollectionSpec":
        if self.kind == "feed" and self.feed_type is None:
            raise ValueError("feed_type is required when kind=feed")
        if self.kind != "feed" and self.feed_type is not None:
            raise ValueError("feed_type is only valid when kind=feed")
        if self.kind == "user-posts" and not self.target:
            raise ValueError("target is required when kind=user-posts")
        if self.kind not in {"user-posts", "likes"} and self.target is not None:
            raise ValueError("target is only valid when kind=user-posts or kind=likes")
        if self.kind not in {"bookmarks", "likes"} and self.remove_after_collect:
            raise ValueError("remove_after_collect is only valid when kind=bookmarks or kind=likes")
        return self

    @property
    def stage_name(self) -> str:
        if self.name:
            return self.name
        if self.kind == "feed":
            return f"feed-{self.feed_type}"
        if self.kind == "user-posts":
            return f"user-posts-{self.target}"
        if self.kind == "likes" and self.target:
            return f"likes-{self.target}"
        return self.kind


class CollectorConfig(BaseModel):
    collections: list[CollectionSpec] = Field(default_factory=list)


def resolve_config_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    env_path = os.environ.get("TWITTER_COLLECTOR_CONFIG")
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


def load_config(path: str | Path | None = None) -> CollectorConfig:
    config_path = resolve_config_path(str(path) if path is not None else None)
    raw = yaml.safe_load(config_path.read_text()) or {}
    return CollectorConfig.model_validate(raw)
