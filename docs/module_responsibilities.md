# モジュール責務一覧

## schemas/
**責務**: 全データ構造の型定義（Pydantic BaseModel）

| ファイル | 責務 |
|---|---|
| race.py | レース・出走馬・結果・過去走のスキーマ |
| prediction.py | 予測出力・Gate判定・映像観測・理由コードのスキーマ |
| judgment_log.py | 判定ログ・監視スナップショットのスキーマ |

## data_quality/
**責務**: 入力データの品質保証とリーケージ防止

| ファイル | 責務 |
|---|---|
| validators.py | 必須列・重複・欠損率・範囲のバリデーション |
| leakage_guard.py | 時系列分割管理、未来情報混入チェック、禁止列アサーション |

## core/
**責務**: 予測モデルの学習・推論。ranking, 勝率, 複勝圏, market統合

| ファイル (Phase 2) | 責務 |
|---|---|
| features.py | 特徴量エンジニアリング |
| ranking_model.py | LightGBM ランキングモデル |
| win_model.py | 勝率モデル（2クラス分類） |
| place_model.py | 複勝圏モデル（2クラス分類） |
| market.py | オッズ→市場確率変換、edge計算 |
| baseline.py | popularity baseline |

## gate/
**責務**: no-bet / bet の判定。理由コード付与

| ファイル (Phase 2) | 責務 |
|---|---|
| decision.py | Gate 判定ロジック |
| thresholds.py | 判定閾値の管理 |

## race_video/
**責務**: レース映像からの観測事実の記録。Core非依存

| ファイル (Phase 3) | 責務 |
|---|---|
| observer.py | タグ入力・バリデーション |
| comment.py | 半構造化コメント生成 |
| recurrence.py | 再発度算出 |

## paddock/
**責務**: パドック観測。3モード対応

| ファイル (Phase 4) | 責務 |
|---|---|
| observer.py | 状態・トレンド判定入力 |
| danger.py | 危険人気馬検知 |
| scoring.py | condition_score 算出 |

## warmup/
**責務**: 返し馬観測。3モード対応

| ファイル (Phase 4) | 責務 |
|---|---|
| observer.py | 直前状態判定入力 |
| anomaly.py | 直前異常検知 |
| scoring.py | warmup_score 算出 |

## integration/
**責務**: 全サブシステムのスコア統合・最終判定

| ファイル (Phase 3-4) | 責務 |
|---|---|
| normalizer.py | score共通尺度化 [0,1] |
| combiner.py | 重み付き統合 |
| veto.py | 映像系拒否権（video_veto, paddock_alert, warmup_alert） |
| divergence.py | condition_vs_market, condition_vs_core |

## monitoring/
**責務**: ROI監視・衝突率・強制停止・判定ログ永続化

| ファイル (Phase 2) | 責務 |
|---|---|
| logger.py | JudgmentLog の永続化（SQLite） |
| roi_tracker.py | 累積・直近ROI算出 |
| conflict.py | Core vs 映像系 衝突率 |
| halt.py | 強制停止判定・解除 |

## cli/
**責務**: ユーザーインターフェース（click ベース）

| ファイル | 責務 |
|---|---|
| main.py | 全コマンド定義・ルーティング |
