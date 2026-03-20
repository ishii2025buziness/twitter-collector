"""twitter-cli backed collection helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import import_module

from config import CollectionSpec


@dataclass(slots=True)
class CollectionPayload:
    stage_name: str
    items: list[dict]
    warnings: list[str]


class TwitterCliCollector:
    """Thin wrapper around twitter-cli's Python API."""

    def _get_client(self):
        auth_module = import_module("twitter_cli.auth")
        client_module = import_module("twitter_cli.client")
        cookies = auth_module.get_cookies()
        return client_module.TwitterClient(cookies["auth_token"], cookies["ct0"])

    def _serialize_tweets(self, tweets: list[object]) -> list[dict]:
        serialization_module = import_module("twitter_cli.serialization")
        return json.loads(serialization_module.tweets_to_json(tweets))

    def remove_bookmarks(self, tweet_ids: list[str]) -> dict[str, object]:
        client = self._get_client()
        removed_ids: list[str] = []
        failed_ids: list[dict[str, str]] = []
        for tweet_id in tweet_ids:
            try:
                client.unbookmark_tweet(tweet_id)
                removed_ids.append(tweet_id)
            except Exception as exc:
                failed_ids.append({"id": tweet_id, "error": str(exc)})
        return {
            "remove_after_collect": True,
            "action": "unbookmark",
            "removed_count": len(removed_ids),
            "removed_ids": removed_ids,
            "failed_count": len(failed_ids),
            "failed": failed_ids,
        }

    def remove_likes(self, tweet_ids: list[str]) -> dict[str, object]:
        client = self._get_client()
        removed_ids: list[str] = []
        failed_ids: list[dict[str, str]] = []
        for tweet_id in tweet_ids:
            try:
                client.unlike_tweet(tweet_id)
                removed_ids.append(tweet_id)
            except Exception as exc:
                failed_ids.append({"id": tweet_id, "error": str(exc)})
        return {
            "remove_after_collect": True,
            "action": "unlike",
            "removed_count": len(removed_ids),
            "removed_ids": removed_ids,
            "failed_count": len(failed_ids),
            "failed": failed_ids,
        }

    def collect(self, spec: CollectionSpec) -> CollectionPayload:
        client = self._get_client()
        if spec.kind == "feed":
            if spec.feed_type == "following":
                tweets = client.fetch_following_feed(spec.max_items)
            else:
                tweets = client.fetch_home_timeline(spec.max_items)
            return CollectionPayload(stage_name=spec.stage_name, items=self._serialize_tweets(tweets), warnings=[])

        if spec.kind == "bookmarks":
            tweets = client.fetch_bookmarks(spec.max_items)
            items = self._serialize_tweets(tweets)
            return CollectionPayload(
                stage_name=spec.stage_name,
                items=items,
                warnings=[],
            )

        if spec.kind == "likes":
            if spec.target:
                profile = client.fetch_user(spec.target)
            else:
                profile = client.fetch_me()
            tweets = client.fetch_user_likes(profile.id, spec.max_items)
            items = self._serialize_tweets(tweets)
            return CollectionPayload(
                stage_name=spec.stage_name,
                items=items,
                warnings=[],
            )

        if spec.kind == "user-posts":
            profile = client.fetch_user(spec.target or "")
            tweets = client.fetch_user_tweets(profile.id, spec.max_items)
            return CollectionPayload(stage_name=spec.stage_name, items=self._serialize_tweets(tweets), warnings=[])

        raise RuntimeError(f"Unsupported collection kind: {spec.kind}")
