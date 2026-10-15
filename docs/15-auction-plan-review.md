# オークション実装計画の確認記録（2026-10-16）

ユーザーから提示された `PLAN.md` と実装・仕様・テストを照合した。機能は実装済みだが、画面遷移と破損データ検査に問題があり修正した。Discord実機での一連の操作確認は未実施のため、計画全体の検証完了とは扱わない。

## 計画との照合

| 計画の項目 | 実装の一次根拠 | 確認結果 |
|---|---|---|
| Lv7・全サーバー共通・自己購入禁止・ゲーム内名 | `core/auction.py:require_access / buy_listing`、`cogs/auction.py`、`views/auction_view.py` | 実装・隔離テスト済 |
| 同じid/metaの在庫、正整数の数量/総額、期間別手数料、売主へ全額支払 | `core/auction.py:create_listing / fee_for / buy_listing` | 実装・隔離テスト済。装備中の品物は出品対象外、手数料返金なし |
| UUID出品ID・5項目の保存形式・metaの深いコピー・取引後削除 | `core/auction.py`、`core/storage.py:validate` | 実装・隔離テスト済 |
| 確認時は未消費、確定時の再検索/数量/残高/レベル検査 | `ConfirmView`、`core/auction.py:create_listing` | 実装・隔離テスト済 |
| 購入・取消・期限切れの競合と期限境界 | `core/auction.py`、`tests/test_auction.py` | 同じ保存ロック内でawaitなし。競合・境界テスト済 |
| 起動時・毎秒の期限切れ返却、管理者移行 | `core/__init__.py`、`core/background.py:update_tick`、`core/auction.py:transit_user` | 実装・隔離テスト済。移行先プロフィールの置換は既存仕様 |
| 新着順25件・空一覧・自分の出品・詳細・在庫/Modal/期間/確認 | `views/auction_view.py`、`modals/auction_modal.py` | 実装・UIフェイクテスト済 |
| 全画面ephemeral・所有者制限・180秒失効・具体的エラー・保存後通知 | 同上、`views/_timeout.py` | 実装済。旧Viewの停止漏れを修正し回帰テスト追加 |
| 二ファイルの復旧ジャーナル・原子的置換・fsync・確定後停止 | `core/storage.py:commit / recover` | 保存各段階への障害注入・再適用の非重複を検証済 |
| 初回初期化・破損時のログ/バックアップ/起動中止 | `core/storage.py`、`core/state.py:_load_users` | ユーザー検査不足を修正。不正データを復旧前に拒否するテスト追加 |
| Docker既存ボリューム・権限・symlink・除外設定 | `Dockerfile`、`docker-entrypoint.sh`、`compose.yaml`、`.gitignore`、`.dockerignore` | 隔離Dockerで検証済 |
| 仕様更新・全自動テスト・Dockerコンパイル | `docs/06-features/auction-house.md`、`tests/` | 仕様・受入条件更新、全78テストとDocker全工程成功 |
| Discord実機の画面遷移・コマンド同期・描画 | `docs/14-manual-discord-verification.md` | **未実施**。隔離テストBot・サーバー未指定。フェイクテストと区別する |

## 修正した問題

1. **旧Viewのタイムアウトによる画面上書き**: 戻る・中止・在庫ページ送り・Modal入力後などで旧Viewが生存していた。同じメッセージを置換する前に旧Viewを停止し、停止後のタイムアウト編集を抑止した。Modalをキャンセルした場合は元の在庫画面を使える。
2. **不正な復旧スナップショットの適用**: 検査対象が出品者に限られ、出品が空なら `users: {"1": null}` などを復旧して正常ファイルを置換できた。通常読込・復旧とも全ユーザーの取引関連フィールドと全在庫を検査するようにし、重複JSONキー・非有限数値も拒否した。失敗時はデータを保持し、バックアップとログを残して終了する。

両問題は修正前の追加テストで失敗を確認し、修正後の成功を確認した。

## 検証結果と範囲

- ローカル: Python 3.14.7、一時venv、固定依存関係で全78テスト成功。`pip check`、シェル構文検査、差分の空白検査も成功。
- Docker: 固定イメージ・Python 3.12.13でビルド、依存検査、全ソースのコンパイル、全78テストが成功。別コンテナで既存ボリューム初期化、出品保持、停止中期限切れ、復旧/再適用、破損・不正ユーザーでの起動拒否とバックアップ・正常ファイル保持まで成功。
- ダミー設定・使い捨てボリューム・外部通信なしで実行し、専用コンテナ・ボリューム・イメージタグは削除した。実運用データには触れていない。
- 残る確認はDiscord実機操作（ACR-AUC-11）。コード上の未実装機能は今回の照合範囲では見つからなかった。

受入条件: [12-testable-acceptance-criteria.md](12-testable-acceptance-criteria.md)、仕様: [06-features/auction-house.md](06-features/auction-house.md)。
