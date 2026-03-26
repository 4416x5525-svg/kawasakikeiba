# Data Dictionary

## 概要
川崎競馬 意思決定AIシステムで使用する全データの定義。

---

## 1. 入力データ

### 1.1 RaceRecord（レース基本情報）
| フィールド | 型 | 説明 | 例 |
|---|---|---|---|
| race_id | str | 一意識別子 YYYYMMDD_KW_RR | 20260301_KW_07 |
| race_date | date | 開催日 | 2026-03-01 |
| race_number | int(1-12) | レース番号 | 7 |
| distance | int | 距離(m) | 1500 |
| track_condition | enum | 馬場状態 good/slightly_heavy/heavy/bad | good |
| grade | enum | 格付け C3〜S, open, stakes | B2 |
| num_runners | int(2-16) | 出走頭数 | 12 |
| post_time | datetime? | 発走時刻 | 2026-03-01T15:30 |

### 1.2 HorseEntry（出走馬情報）
| フィールド | 型 | 説明 |
|---|---|---|
| race_id | str | レースID |
| horse_id | str | 馬ID |
| horse_name | str | 馬名 |
| post_position | int(1-16) | 枠番 |
| horse_number | int(1-16) | 馬番 |
| jockey_id | str | 騎手ID |
| jockey_name | str | 騎手名 |
| trainer_id | str | 調教師ID |
| weight_carried | float | 斤量(kg) |
| horse_weight | int? | 馬体重(kg) |
| horse_weight_change | int? | 馬体重増減(kg) |
| odds_win | float? | 単勝オッズ（確定） |
| popularity | int? | 単勝人気順 |

### 1.3 PastPerformance（過去走）
| フィールド | 型 | 説明 |
|---|---|---|
| horse_id | str | 馬ID |
| race_id | str | レースID |
| race_date | date | レース日 |
| distance | int | 距離(m) |
| track_condition | enum | 馬場状態 |
| finish_position | int | 着順 |
| num_runners | int | 出走頭数 |
| odds_win | float? | 単勝オッズ |
| finish_time | float? | 走破タイム(秒) |
| last_3f | float? | 上がり3F(秒) |
| corner_positions | str? | コーナー通過順 |
| horse_weight | int? | 馬体重(kg) |
| weight_carried | float | 斤量(kg) |
| jockey_id | str | 騎手ID |
| grade | enum | 格付け |

### 1.4 RaceResult（レース結果）
| フィールド | 型 | 説明 |
|---|---|---|
| race_id | str | レースID |
| horse_id | str | 馬ID |
| horse_number | int | 馬番 |
| finish_position | int | 着順 |
| finish_time | float? | 走破タイム(秒) |
| margin | str? | 着差 |
| last_3f | float? | 上がり3F(秒) |
| corner_positions | str? | コーナー通過順 |

---

## 2. 中間データ（モデル出力）

### 2.1 CorePrediction
| フィールド | 型 | 説明 |
|---|---|---|
| rank_score | float | ランキングスコア（相対順位用） |
| win_prob | float [0,1] | 勝率推定値 |
| place_prob | float [0,1] | 複勝圏推定値 |
| market_win_prob | float [0,1] | 市場推定勝率 |
| edge_win | float | win_prob - market_win_prob |
| edge_place | float | place_prob - market推定複勝圏率 |

### 2.2 GateDecision
| フィールド | 型 | 説明 |
|---|---|---|
| decision | str | "bet" or "no_bet" |
| no_bet_reasons | list[enum] | no-bet 理由コード群 |
| bet_reasons | list[enum] | bet 理由コード群 |
| confidence | float [0,1] | 判定信頼度 |

---

## 3. 映像系データ（保存対象はタグ・スコア・コメントのみ）

### 3.1 VideoObservation
| フィールド | 型 | 説明 |
|---|---|---|
| tags | list[enum] | レース映像タグ（観測事実のみ） |
| comment | str | 半構造化コメント |
| recurrence_score | float? [0,1] | 再発度 |

### 3.2 PaddockObservation
| フィールド | 型 | 説明 |
|---|---|---|
| state | enum | good / neutral / bad |
| trend | enum | improving / stable / declining |
| danger_popular | bool | 危険人気馬フラグ |
| tags | list[str] | 観測タグ |
| comment | str | コメント |

### 3.3 WarmupObservation
| フィールド | 型 | 説明 |
|---|---|---|
| state | enum | good / neutral / bad |
| anomaly_detected | bool | 直前異常フラグ |
| tags | list[str] | 観測タグ |
| comment | str | コメント |

---

## 4. 出力データ（保存対象）

### 4.1 JudgmentLog
最終判定の全情報を保持するログレコード。詳細は `schemas/judgment_log.py` を参照。

### 4.2 MonitoringSnapshot
ROI・衝突率・強制停止状態の定期スナップショット。

---

## 5. データソース制約

- 川崎競馬の公式データのみ使用
- 非公式スクレイピングデータは使用禁止
- 映像は公式配信を視聴利用。映像ファイルの保存は行わない
- 確定オッズは予測時特徴量として使用禁止（リーケージ）
- 解説・番組コメントは参考表示のみ。主判定への使用禁止

## 6. ID体系

| ID | 形式 | 例 |
|---|---|---|
| race_id | YYYYMMDD_KW_RR | 20260301_KW_07 |
| horse_id | 地方競馬の馬登録番号 | 実データ依存 |
| jockey_id | 騎手コード | 実データ依存 |
| trainer_id | 調教師コード | 実データ依存 |
