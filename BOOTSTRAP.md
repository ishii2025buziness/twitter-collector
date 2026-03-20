# Bootstrap

このファイルが存在する = 未セットアップ。
セットアップ完了後にこのファイルを削除すること。

## ヒアリング方法

ユーザーへの質問はインタラクティブなツールを使うこと：

- **Claude Code** — `AskUserQuestion` ツールを使う（選択肢を提示してユーザーが選べる）
- **その他のエージェント** — 同等のインタラクティブUIツールがあれば使う。なければ1問ずつ質問して回答を待つ

## 手順

### 1. サービス名を設定

`service.config.yaml` を作成：

```yaml
service_name: <サービス名をここに記入>
artifact_root: .artifacts
infra:
  url: https://github.com/ishii2025buziness/k12-network-notes  # デフォルト。変える場合はここを書き換える
  type: k12
```

### 2. infra参照を clone する

デフォルト（k12-network-notes）の場合：

```bash
git clone https://github.com/ishii2025buziness/k12-network-notes infra
```

別のインフラを使う場合は `service.config.yaml` の `infra.url` を変更してから上記コマンドのURLを差し替える。

これは deploy 先インフラを近くで参照するための clone であり、編集の正本を service repo に持つためではない。
host wiring の変更が必要なら、infra 本体 repo 側で commit / review すること。

### 3. infraのデータパスを確認する

`infra/` のマウント定義を読み、コンテナの `/data` がホストのどこにマウントされるかを確認する。
`service.config.yaml` の `artifact_root` をそのパスに合わせること。

確認先の目安:

- `infra/nixos/modules/` の service module
- `infra/nixos/hosts/` の host import / enable
- `infra/containers/` の compose, Containerfile, systemd 関連ファイル

### 3.5. common/ を submodule として登録

既に `common/` ディレクトリが存在する場合は先に削除する：

```bash
rm -rf common/
```

submodule として登録：

```bash
git submodule add https://github.com/ishii2025buziness/pipeline-common common
```

> **注意**: `common/` をそのままコピーした場合、内部に `.git/` が残っていると
> GitHub に push されず、K12 で clone 後に `common/` が空になりビルドが失敗する。
> 必ず submodule として登録すること。

### 4. app/pyproject.tomlのservice_nameを更新

`app/pyproject.toml` の `name = "service-name"` を実際のサービス名に変更。

### 5. app/src/pipeline.py の job 名を更新

`service-name` のダミー値を実際のサービス名に変更。

### 6. container/entrypoint.sh をカスタマイズ

`container/entrypoint.sh` のデフォルト値を確認・修正する：

- `PACKAGE_DIR`: `app/` 配置なら `/app/app`、ルート直下なら `/app`
- `PYTHONPATH`: common を含む場合は `/app/common/src:/app/app/src`
- サービス固有の auth setup（トークン配置、ログイン処理等）があれば冒頭に追加

```bash
# 例: app/ 配置の場合
PACKAGE_DIR=/app/app
# 例: common を含む場合
PYTHONPATH=/app/common/src:/app/app/src \
```

### 7. container/Containerfile をカスタマイズ

サービスが必要とする追加依存パッケージを確認・追記する：

- `pip install` に追加パッケージを記載（例: `playwright`, `wrangler`）
- Node.js / npm が必要なら `apt-get install` に追加
- ビルド時の build context は `app/ common/ container/` を渡すこと（Containerfile 冒頭コメント参照）

### 8. このファイルを削除

```bash
git rm BOOTSTRAP.md
git commit -m "bootstrap: initialize <サービス名>"
```

## 次のステップ

セットアップ完了後は `docs/deploy.md` の手順に従って
infra repo を更新し、K12 にデプロイする。
