## うるさいやつbot
リファクタリング用ブランチ。

## 説明
変更点
- main.pyを分割して、cogs/coreフォルダに分割(30ファイルほど)
- bot終了時に出るエラーを修正 state.py 197行目
- leaderboardにあったChoicesと実装のズレを修正 leaderboard.py 35~73行目あたり
- 起動直後にbotが終了するとエラーが出る問題を修正。 state.py 208行目

## ライセンス
[LICENSE.md](LICENSE.md)を参照
