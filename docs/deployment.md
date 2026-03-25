# デプロイ方針 — Twitter Collector

## デプロイ先

**K12 NixOS (uv2nix + systemd oneshot service)**

## 概要

- このサービスは `claude -p` を呼ばないため、**NixOS container 隔離は不要**
- 単純な systemd oneshot service として直接実行される
- Podman/Containerfile/GHCRへのpushは不要（廃止済み）

## 依存パッケージ

- `twitter-cli` は PyPI 未公開の git パッケージ
  - uv2nix で git dep として処理される
  - ref: `git+https://github.com/jackwener/twitter-cli.git@e496d8f`

## k12-network-notes 管理ファイル

- `nixos/modules/twitter-collector.nix` — systemd oneshot service設定
- `nixos/packages/twitter-collector.nix` — uv2nixパッケージ定義

## 廃止済み

- Podman/Containerfile/GHCR（ADR-0004により廃止）
