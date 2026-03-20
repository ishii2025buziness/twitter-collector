# Architecture

このテンプレートの設計意図と決定理由を記録する。

## 基本方針

新サービスを作るたびに複数のリポジトリを理解しないといけない問題を解決するため、
このテンプレートを使えば必要な知識が一箇所に揃う状態にする。

## 設計決定

### 共通インタフェース（python -m cli run/smoke/check）

**理由:** K12のsystemdタイマーやモニタリングがサービスの中身を知らなくても
統一的に呼び出せるようにするため。サービスごとに呼び出し方が違うと管理コストが増える。

### pipeline-common を submodule にする

**理由:** DRY原則。contracts.py / job_cli.py 等を各サービスにコピーすると、
変更時に全サービスを個別に更新する必要が生じる。submoduleなら
`git submodule update --remote` で全サービスに伝播できる。

### Containerfile / entrypoint.sh はコピー（submoduleではない）

**理由:** サービスごとの差分（依存パッケージ、認証設定等）が大きく、
共通化しようとすると条件分岐だらけになって逆に複雑になるため。
ひな形としてコピーして使う。

### infra は bootstrap 時に設定する（テンプレに固定しない）

**理由:** インフラが変わったとき（K12 → VPS等）にテンプレ自体を
作り直さずに済むようにするため。`infra/` 配下に関連 infra repo を clone して参照できるようにする。

### サービス固有の build 定義は service repo に置く

**理由:** `Containerfile` や `entrypoint.sh` はサービス自身の正本であり、
host 固有 wiring とは責務が異なるため。各サービス repo に残した方が変更理由が追いやすい。

### host wiring は infra repo の責務とする

**理由:** systemd、mount、port、secret 配線、NixOS module は host 側の状態そのものであり、
サービス repo に混ぜると責務が曖昧になるため。

### infra clone は参照用であり、編集の正本ではない

**理由:** 近くに置いて参照する利便性はあるが、実際の変更単位は infra 本体 repo にある。
service repo の一部のように扱うと commit/push の単位が曖昧になりやすい。

### docs/ による progressive disclosure

**理由:** AGENTS.mdにすべての情報を書くとコンテキストが膨大になる。
将来のエージェントが必要とする知識だけをdocs/に残し、
AGENTS.mdは目次として機能させる。
