# kawasaki-keiba プロジェクト

## 概要
川崎競馬限定の意思決定AIシステム。Python package + CLI。

## 原則
- 川崎競馬のみ対象
- 購入単位100円、コストモデルなし、同時レースなし
- 映像は公式配信を視聴利用。映像そのものは保存しない
- 保存対象: タグ、スコア、コメント、理由コード、判定ログのみ
- 解説・番組コメントは参考表示のみ。主判定に使わない
- 映像判断は「見たままの観測事実」のみ
- 主観表現・能力断定・未来情報禁止
- ランダム分割禁止。時系列評価のみ
- popularity baseline を必ず用意する
- no-bet を中心機能にする
- 映像系は Core と分離した独立システム
- ノートブック中心にしない

## ディレクトリ構成
- `src/kawasaki_keiba/` — メインパッケージ
- `tests/` — テスト (モジュール別)
- `docs/` — 設計文書

## 開発コマンド
```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
mypy src/
kawasaki --help
```
