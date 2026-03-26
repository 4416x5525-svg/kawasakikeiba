# CLI 仕様

## 概要
`kawasaki` コマンドで全機能にアクセスする。click ベース。

## コマンド一覧

### データ品質
```
kawasaki validate <data_dir>
```
- データ品質チェック（バリデーション + リーケージチェック）を実行
- 実装: Phase 2

### Core 予測
```
kawasaki predict <race_id> [--popularity-baseline]
```
- Core モデルで予測を実行
- `--popularity-baseline`: 人気順ベースラインとの比較を表示
- 実装: Phase 2

### Gate 判定
```
kawasaki gate <race_id>
```
- no-bet / bet 判定を実行
- 理由コードを表示
- 実装: Phase 2

### Race Video
```
kawasaki video tag <race_id>
```
- レース映像の観測タグを入力・記録する
- 対話形式で馬番ごとにタグ・コメントを入力
- 実装: Phase 3

### Paddock
```
kawasaki paddock observe <race_id> [--mode off|advisory|integrated]
```
- パドック観測を入力・記録する
- `--mode`: 動作モード（デフォルト: off）
- 実装: Phase 4

### Warmup
```
kawasaki warmup observe <race_id> [--mode off|advisory|integrated]
```
- 返し馬観測を入力・記録する
- `--mode`: 動作モード（デフォルト: off）
- 実装: Phase 4

### Integration
```
kawasaki integrate <race_id>
```
- 全サブシステムのスコアを統合し最終判定を出力
- 実装: Phase 3-4

### Monitoring
```
kawasaki monitor status
kawasaki monitor roi [--recent N]
```
- `status`: 現在の監視ステータス（強制停止中か等）
- `roi`: ROI表示。`--recent`で直近Nレース（デフォルト30）
- 実装: Phase 2

### 判定ログ
```
kawasaki log show <race_id>
```
- 指定レースの判定ログを表示
- 実装: Phase 2

## race_id 形式
`YYYYMMDD_KW_RR` (例: `20260301_KW_07`)

## 出力形式
- デフォルト: rich による整形テーブル出力
- `--json` オプション（将来）: JSON出力
