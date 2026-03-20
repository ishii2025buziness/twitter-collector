# Deploy Workflow

service-template から作られたサービスを runtime host へ載せるときの標準手順。

この文書の目的は、service repo、infra repo、host 上の手作業の境界を固定し、agent ごとのぶれを減らすことにある。

## Responsibility Split

### Service Repo

service repo が正本として持つもの:

- アプリ本体
- `Containerfile`
- `entrypoint.sh`
- service-level 設定の雛形
- API / CLI / skill
- サービス固有の healthcheck や起動方法

### Infra Repo

infra repo が正本として持つもの:

- host import / module enable
- systemd / NixOS unit
- port / mount / secret wiring
- reverse proxy や firewall の配線
- どの host に何を載せるかという宣言

### Runtime Host

host 上で直接行うもの:

- 一時的な検証
- 暫定 deploy
- live health / E2E 確認

host 上の手作業は、最終的には service repo または infra repo のどちらかへ回収する。

## Rules

- service repo だけでは deploy が完結しない場合、infra repo も変更対象に含める
- infra repo が別 repo でも、責務上必要なら変更してよい
- service repo 内の `infra/` は参照用 clone であり、編集の正本ではない
- infra 変更は infra 本体 repo で commit / review する
- `Containerfile` などサービス固有の build 定義は service repo を正本とする

## Standard Flow

1. service repo でサービス本体を実装する
2. service repo だけで deploy できるか判定する
3. host wiring が必要なら infra repo に変更を入れる
4. host に deploy する
5. live health と E2E を確認する
6. 手作業が残ったら、service repo か infra repo に回収する

## Step 1: Implement In Service Repo

最低限ここまでを service repo に入れる:

- `Containerfile`
- `entrypoint.sh`
- 起動コマンド
- README の利用入口
- API 契約
- 必要なら client CLI / skill

この段階では host 固有の mount path や systemd unit までは入れない。

## Step 2: Decide Whether Infra Changes Are Needed

以下のどれかが必要なら infra repo も変更対象:

- 新しい port を開ける
- secret / credentials の配置を定義する
- mount path を固定する
- systemd / NixOS module を追加する
- reverse proxy や firewall を触る

ローカル実装や単体テストだけなら service repo だけでよい。

## Step 3: Update Infra Repo

infra repo でやること:

- service を host config に import / enable する
- port / volume / env / secret path を配線する
- 必要なら build / run の unit を追加する

NixOS module テンプレは `nixos/modules/service-name.nix` を参照。

> **注意: ホスト側 loopback サービスへの接続**
> `claude-gateway` など `127.0.0.1` にバインドしているホスト側サービスへ
> コンテナから接続するには `--network=host` が必要。
> デフォルトの bridge ネットワークからは `127.0.0.1` に届かず `Connection refused` になる。
> NixOS module テンプレのコメントアウトされた `"--network=host"` 行を有効化すること。

service repo の `infra/` ディレクトリを、そのまま service repo の一部だと思わないこと。
正本は infra 本体 repo である。

## Step 4: Deploy To Host

基本は infra repo の宣言に沿って反映する。

暫定的に host 上で手動 deploy する場合でも、以下は残す:

- 何を手動で入れたか
- どこがまだ宣言化されていないか
- live 検証結果

## Step 5: Verify

最低限の確認:

- health endpoint
- 1 件の live E2E
- ログ出力
- secret / credential path の読込

## Step 6: Reconcile Temporary Work

host で直接入れたものは放置しない。

- サービス固有なら service repo に戻す
- host wiring なら infra repo に戻す

「今動いているがコード化されていない」状態を長く残さない。
