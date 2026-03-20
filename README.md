# Service Template

新しいサービスを作るときのひな形リポジトリ。

- `app/` — Pythonサービス本体（run/smoke/check CLI）
- `common/` — 共通contracts（pipeline-common submodule）
- `container/` — サービス側が正本として持つ `Containerfile` / `entrypoint.sh`
- `infra/` — deploy先インフラの参照用 clone
- `docs/` — 設計、契約、deploy workflow

## Responsibility Split

- service repo は、アプリ本体、`Containerfile`、entrypoint、service-level 設定、API/CLI/skill を持つ
- infra repo は、host import、systemd、mount、secret 配線、port、proxy など host wiring を持つ
- host 上の手作業は一時的な検証のみに留め、最終的に service repo か infra repo へ回収する

deploy の標準フローは [docs/deploy.md](/home/kento/projects/0318/service-template/docs/deploy.md) を参照。
