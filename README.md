## うるさいやつbot
リファクタリング用ブランチ。

## 変更点
- main.pyを分割して、cogs/coreフォルダに分割(30ファイルほど)
- bot終了時に出るエラーを修正 state.py 197行目
- leaderboardにあったChoicesと実装のズレを修正 leaderboard.py 35~73行目あたり
- 起動直後にbotが終了するとエラーが出る問題を修正。 state.py 208行目
- json.dumpをcore/utilsの共通関数に置換
  - save_user() save_market() save_data() をそれぞれ置き換えました

## ライセンス
[LICENSE.md](LICENSE.md)を参照
