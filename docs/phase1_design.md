# Phase 1 設計書

## 目的
プロジェクトの土台を構築する。スキーマ・データ品質・リーケージガード・全モジュールのI/O設計を確定させ、Phase 2 以降の実装を安全に進められる状態にする。

---

## 1. プロジェクト構成

```
kawasaki-keiba/
├── pyproject.toml              # パッケージ定義
├── CLAUDE.md                   # プロジェクト規約
├── docs/
│   ├── data_dictionary.md      # 全データ定義
│   ├── assumptions_and_limits.md # 前提条件と限界
│   ├── phase1_design.md        # 本文書
│   ├── cli_spec.md             # CLI仕様
│   └── module_responsibilities.md # モジュール責務一覧
├── src/kawasaki_keiba/
│   ├── __init__.py
│   ├── schemas/                # Pydantic スキーマ
│   │   ├── race.py             # レース・出走馬・結果・過去走
│   │   ├── prediction.py       # 予測・判定・映像観測
│   │   └── judgment_log.py     # 判定ログ・監視スナップショット
│   ├── data_quality/           # データ品質
│   │   ├── validators.py       # 入力データバリデーション
│   │   └── leakage_guard.py    # リーケージ防止
│   ├── core/                   # Core System
│   ├── gate/                   # Gate System
│   ├── race_video/             # Race Video System
│   ├── paddock/                # Paddock System
│   ├── warmup/                 # Warmup System
│   ├── integration/            # Integration Layer
│   ├── monitoring/             # Monitoring / Logging
│   └── cli/                    # CLI
│       └── main.py             # click ベース CLI
└── tests/
    ├── core/
    ├── gate/
    ├── race_video/
    ├── paddock/
    ├── warmup/
    ├── integration/
    └── monitoring/
```

---

## 2. スキーマ設計

### 2.1 入力スキーマ
- **RaceRecord**: レース基本情報。race_id は `YYYYMMDD_KW_RR` 形式
- **HorseEntry**: 出走馬情報。馬番・騎手・斤量等
- **PastPerformance**: 過去走データ。特徴量生成の主要ソース
- **RaceResult**: 着順結果。学習ターゲット

### 2.2 予測スキーマ
- **CorePrediction**: Core の出力。rank_score, win_prob, place_prob, edge
- **GateDecision**: bet/no_bet 判定 + 理由コード
- **NoBetReason / BetReason**: 理由コード enum

### 2.3 映像系スキーマ
- **VideoObservation**: レース映像タグ + コメント + 再発度
- **PaddockObservation**: state + trend + 危険人気馬フラグ
- **WarmupObservation**: state + 異常フラグ
- **RaceVideoTag**: 位置取り・ペース・走行・直線・敗因・勝因の観測タグ enum

### 2.4 出力スキーマ
- **JudgmentLog**: 最終判定の全情報（保存対象）
- **MonitoringSnapshot**: ROI・衝突率・強制停止状態

---

## 3. データ品質設計

### 3.1 validators.py
- `validate_race_entries()`: 必須列存在・重複・欠損率・範囲チェック
- `validate_results()`: 着順連続性チェック
- 川崎固有チェック: 距離 900-2100m

### 3.2 leakage_guard.py
- `TimeSeriesSplit`: train/val/test の時系列分割。順序制約を `__post_init__` で保証
- `check_feature_leakage()`: 結果列・確定オッズの混入チェック
- `FORBIDDEN_FEATURES_AT_PREDICTION_TIME`: 予測時禁止列セット
- `assert_no_forbidden_features()`: 禁止列のアサーション

---

## 4. Core / Gate 最小実装方針 (Phase 2 向け)

### 4.1 Core System

```
入力: HorseEntry[] + PastPerformance[] + RaceRecord
出力: CorePrediction[]
```

**Ranking Model**:
- LightGBM ランキングモデル (lambdarank)
- 特徴量: 過去走成績統計、騎手統計、距離適性、馬場適性、クラス等
- 時系列分割で学習・評価

**勝率モデル**:
- 2クラス分類 (1着 vs それ以外)
- calibrated probability を出力

**複勝圏モデル**:
- 2クラス分類 (3着以内 vs それ以外)
- calibrated probability を出力

**Market統合**:
- 単勝オッズ → 市場推定勝率に変換
- edge = model_prob - market_prob
- popularity baseline: 人気順 = 予測順のベースライン

### 4.2 Gate System

```
入力: CorePrediction[] + RaceRecord
出力: GateDecision
```

**判定ロジック（初期版）**:
1. max(edge_win) が閾値未満 → no_bet (NO_EDGE)
2. 全馬の win_prob 最大値が閾値未満 → no_bet (LOW_CONFIDENCE)
3. 過去走データ不足馬が多すぎる → no_bet (INSUFFICIENT_DATA)
4. 少頭数 (<=4) → no_bet (SMALL_FIELD)
5. 上記いずれにも該当しない → bet 候補

閾値は validation set で調整。

---

## 5. 映像系 I/O 設計 (Phase 3-4 向け)

### 5.1 Race Video System

```
入力:
  - race_id
  - 対象馬番リスト
  - 人間の観測入力（CLI経由）

出力:
  - VideoObservation[] (1頭ごと)

保存:
  - tags, comment, recurrence_score のみ
  - 映像ファイルは保存しない
```

**タグ体系**: `RaceVideoTag` enum で定義済み。位置取り・ペース・走行・直線・敗因・勝因の6カテゴリ。

**コメント形式**: 半構造化。「{位置取り} → {直線} → {結果}」のテンプレートに沿った自由記述。

**再発度**: 0（偶発的）〜1（構造的）。過去の同一馬のタグパターンから算出。

### 5.2 Paddock System

```
入力:
  - race_id
  - 動作モード (off / advisory / integrated)
  - 人間の観測入力（CLI経由）

出力:
  - PaddockObservation[] (1頭ごと)
  - danger_popular_horses: list[int]  # 危険人気馬の馬番

統合への出力 (advisory / integrated):
  - condition_score: float per horse
  - danger_flag: bool per horse
```

### 5.3 Warmup System

```
入力:
  - race_id
  - 動作モード (off / advisory / integrated)
  - 人間の観測入力（CLI経由）

出力:
  - WarmupObservation[] (1頭ごと)

統合への出力 (advisory / integrated):
  - warmup_score: float per horse
  - anomaly_flag: bool per horse
```

### 5.4 映像系の独立性保証
- 映像系は Core の出力を**入力として受け取らない**
- 観測はオッズ・予測値を見ずに行う（バイアス防止）
- 統合は Integration Layer でのみ実施

---

## 6. Integration Layer I/O 設計

```
入力:
  - CorePrediction[]
  - GateDecision
  - VideoObservation[]?  (あれば)
  - PaddockObservation[]?  (あれば)
  - WarmupObservation[]?  (あれば)
  - 各サブシステムの動作モード

出力:
  - 最終 GateDecision (映像系拒否権を反映)
  - 統合スコア (integrated モード時)
  - JudgmentLog

統合ルール:
  1. score共通尺度化: 各サブシステムのスコアを [0, 1] に正規化
  2. 重み付き統合: Core主導、映像系は調整
  3. 映像系拒否権: video_veto / paddock_alert / warmup_alert → 強制 no_bet
  4. condition_vs_market: 映像系評価と市場評価の乖離を検出
  5. condition_vs_core: 映像系評価とCore評価の乖離を検出
```

---

## 7. Monitoring I/O 設計

```
入力:
  - JudgmentLog の蓄積
  - RaceResult (事後)

出力:
  - MonitoringSnapshot
  - 強制停止判定

監視項目:
  - 累積 ROI
  - 直近30レース ROI
  - Core vs 映像系 衝突率
  - 強制停止条件: ROI が閾値 (e.g., 0.7) を下回った場合
```

---

## 8. Phase 2 への引き継ぎ事項

### 実装優先順
1. 特徴量エンジニアリング (core/features.py)
2. Core 3モデル (ranking, win, place)
3. Popularity baseline
4. Market統合
5. Gate 判定ロジック
6. JudgmentLog 永続化
7. 基本 Monitoring

### 必要な外部データ
- 川崎競馬の過去レース結果データ（公式ソースから取得方法を確定する必要あり）
- ID体系の確定（馬ID・騎手ID・調教師IDの具体的なコード体系）

### 未確定事項
- 賭式の選択（単勝 / 複勝 / ワイド / 馬連 等）→ Phase 2 で Core の精度を見て決定
- 特徴量の具体的なリスト → Phase 2 で探索的に決定
- Gate の閾値パラメータ → validation set で調整
