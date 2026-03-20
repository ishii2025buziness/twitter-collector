from __future__ import annotations

from pathlib import Path

import pytest

from config import load_config


def test_load_config_accepts_feed_and_bookmarks(tmp_path: Path):
    config_file = tmp_path / "collections.yaml"
    config_file.write_text(
        """
collections:
  - kind: feed
    feed_type: for-you
    max_items: 10
  - kind: bookmarks
    max_items: 20
    remove_after_collect: true
  - kind: likes
    max_items: 15
    remove_after_collect: true
""".strip()
    )

    config = load_config(config_file)

    assert len(config.collections) == 3
    assert config.collections[0].feed_type == "for-you"
    assert config.collections[1].remove_after_collect is True
    assert config.collections[2].kind == "likes"


def test_load_config_requires_target_for_user_posts(tmp_path: Path):
    config_file = tmp_path / "collections.yaml"
    config_file.write_text(
        """
collections:
  - kind: user-posts
    max_items: 10
""".strip()
    )

    with pytest.raises(Exception):
        load_config(config_file)


def test_load_config_rejects_remove_after_collect_for_non_bookmarks(tmp_path: Path):
    config_file = tmp_path / "collections.yaml"
    config_file.write_text(
        """
collections:
  - kind: feed
    feed_type: following
    max_items: 10
    remove_after_collect: true
""".strip()
    )

    with pytest.raises(Exception):
        load_config(config_file)


def test_load_config_accepts_target_for_likes(tmp_path: Path):
    config_file = tmp_path / "collections.yaml"
    config_file.write_text(
        """
collections:
  - kind: likes
    target: jack
    max_items: 10
""".strip()
    )

    config = load_config(config_file)

    assert config.collections[0].target == "jack"
