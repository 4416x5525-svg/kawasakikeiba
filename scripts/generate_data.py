"""川崎競馬1年分のリアルなサンプルデータを生成する。

実際の川崎競馬のパターンに基づく:
- 開催: 年間約14開催、各開催3-6日、1日10-12レース
- 距離: 900/1400/1500/1600/2000/2100m
- 馬場: 良が60%、稍重20%、重15%、不良5%
- 頭数: 6-14頭（中央値10頭）
- オッズ: 1番人気 1.5-5.0倍、穴馬 20-200倍
"""

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

# 川崎競馬の実パターン
DISTANCES = [900, 1400, 1500, 1600, 2000, 2100]
DISTANCE_WEIGHTS = [0.08, 0.30, 0.25, 0.20, 0.12, 0.05]  # 1400mが最多

GRADES = ["C3", "C2", "C1", "B3", "B2", "B1", "A2", "A1", "open", "stakes"]
GRADE_WEIGHTS = [0.20, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05, 0.04, 0.04, 0.02]

CONDITIONS = ["good", "slightly_heavy", "heavy", "bad"]
CONDITION_WEIGHTS = [0.60, 0.20, 0.15, 0.05]

# 騎手名プール（架空）
JOCKEYS = [
    ("KW_J001", "山田太郎"), ("KW_J002", "佐藤次郎"), ("KW_J003", "鈴木三郎"),
    ("KW_J004", "高橋四郎"), ("KW_J005", "田中五郎"), ("KW_J006", "伊藤六郎"),
    ("KW_J007", "渡辺七郎"), ("KW_J008", "中村八郎"), ("KW_J009", "小林九郎"),
    ("KW_J010", "加藤十郎"), ("KW_J011", "吉田一朗"), ("KW_J012", "松本二朗"),
    ("KW_J013", "井上三朗"), ("KW_J014", "木村四朗"), ("KW_J015", "林五朗"),
]

TRAINERS = [f"KW_T{i:03d}" for i in range(1, 21)]

# 馬名パーツ
NAME_PREFIX = [
    "ゴールド", "シルバー", "ダイヤモンド", "サファイア", "エメラルド",
    "レッド", "ブルー", "グリーン", "ホワイト", "ブラック",
    "サンライト", "ムーンライト", "スター", "キング", "クイーン",
    "ドリーム", "マジック", "ワイルド", "ロイヤル", "ブレイブ",
    "ファイナル", "レジェンド", "フェニックス", "ドラゴン", "タイガー",
    "ストーム", "サンダー", "フラッシュ", "ウインド", "ファイア",
    "ミラクル", "グランド", "ノーブル", "プレシャス", "エターナル",
]
NAME_SUFFIX = [
    "パワー", "スピード", "ハート", "ソウル", "ウェーブ",
    "ナイト", "スカイ", "ロード", "キャッチャー", "ファイター",
    "ブレイカー", "ウォーカー", "ランナー", "クロス", "アロー",
    "フレア", "ガーデン", "ビュー", "コール", "スター",
    "レイン", "フォース", "ブレード", "シグナル", "ダスト",
]

used_names: set[str] = set()
horse_counter = 0


def _gen_horse_name() -> str:
    global horse_counter
    for _ in range(100):
        name = random.choice(NAME_PREFIX) + random.choice(NAME_SUFFIX)
        if name not in used_names:
            used_names.add(name)
            return name
    horse_counter += 1
    name = f"ホース{horse_counter:04d}"
    used_names.add(name)
    return name


def _gen_odds(n: int) -> list[float]:
    """リアルなオッズ分布を生成。1番人気は1.5-5倍、穴馬は高倍率。"""
    # 対数正規分布ベースで生成
    raw = sorted([random.lognormvariate(1.0, 0.8) for _ in range(n)])
    # 1番人気を1.5-5.0に制限
    min_odds = random.uniform(1.5, 5.0)
    raw[0] = min_odds
    # 他をスケーリング
    for i in range(1, n):
        raw[i] = min_odds + (raw[i] - raw[0]) * random.uniform(1.5, 4.0)
    # 端数処理（0.1刻み）
    odds = [round(max(1.1, r), 1) for r in raw]
    return odds


def _gen_corner_positions(n: int, distance: int) -> list[str]:
    """通過順位を生成。先行馬が有利になる傾向を入れる。"""
    num_corners = 2 if distance <= 1000 else 4
    horses = list(range(1, n + 1))

    corners_list = []
    for _ in range(n):
        corners_list.append([])

    # 各コーナーでの順位を生成（前のコーナーから少しずつ変動）
    current_order = list(range(n))
    random.shuffle(current_order)

    for c in range(num_corners):
        # 少しシャッフル
        for i in range(len(current_order) - 1):
            if random.random() < 0.2:
                current_order[i], current_order[i + 1] = current_order[i + 1], current_order[i]
        for rank, horse_idx in enumerate(current_order):
            corners_list[horse_idx].append(rank + 1)

    return ["-".join(str(c) for c in corners) for corners in corners_list]


def _gen_finish(n: int, odds: list[float], corners: list[str]) -> list[int]:
    """着順を生成。オッズ順位と相関を持たせつつ、波乱も起こす。"""
    # オッズが低い（人気がある）馬ほど着順が良い傾向
    scores = []
    for i in range(n):
        odds_rank_score = -math.log(odds[i] + 0.1)  # オッズが低いほどスコアが高い
        noise = random.gauss(0, 0.8)  # ランダム性
        # 先行有利バイアス（川崎の特性）
        first_corner = int(corners[i].split("-")[0]) if corners[i] else n // 2
        pace_bonus = -0.3 * (first_corner / n)  # 先行ほどボーナス
        scores.append(odds_rank_score + noise + pace_bonus)

    # スコア順に着順を割り当て
    ranked = sorted(range(n), key=lambda i: scores[i], reverse=True)
    finish = [0] * n
    for pos, idx in enumerate(ranked):
        finish[idx] = pos + 1
    return finish


def _gen_finish_time(distance: int, finish_pos: int, n: int) -> float:
    """走破タイムを生成。"""
    # 基準タイム（秒）
    base = {900: 54, 1400: 86, 1500: 92, 1600: 100, 2000: 130, 2100: 137}
    t = base.get(distance, 90)
    t += random.gauss(0, 1.5)  # 馬場による変動
    t += (finish_pos - 1) * random.uniform(0.15, 0.4)  # 着差
    return round(t, 1)


def _gen_last_3f(finish_pos: int, n: int) -> float | None:
    """上がり3F。"""
    if random.random() < 0.3:  # 30%の確率で欠損
        return None
    base = 38.0 + random.gauss(0, 1.0)
    base += (finish_pos - 1) * random.uniform(0.1, 0.3)
    return round(base, 1)


def generate_kawasaki_year(year: int = 2025) -> dict:
    """1年分のデータを生成。"""
    # 川崎競馬の開催日程（月ごとの開催日数）
    monthly_days = {
        1: 8, 2: 7, 3: 8, 4: 6, 5: 7, 6: 8,
        7: 6, 8: 7, 9: 6, 10: 8, 11: 7, 12: 6,
    }

    races = []
    global horse_counter
    horse_counter = 0

    for month in range(1, 13):
        num_days = monthly_days[month]
        # 開催日をランダムに配置
        available_days = list(range(1, 29))  # 1-28日
        random.shuffle(available_days)
        race_days = sorted(available_days[:num_days])

        for day in race_days:
            race_date = date(year, month, day)
            num_races = random.randint(10, 12)

            # 当日の馬場状態（同一日は基本同じ、途中変化もあり）
            day_condition = random.choices(CONDITIONS, CONDITION_WEIGHTS)[0]

            for race_num in range(1, num_races + 1):
                # 途中で馬場が変わる可能性（10%）
                if race_num > 6 and random.random() < 0.1:
                    heavier = {"good": "slightly_heavy", "slightly_heavy": "heavy", "heavy": "bad"}
                    day_condition = heavier.get(day_condition, day_condition)

                distance = random.choices(DISTANCES, DISTANCE_WEIGHTS)[0]
                grade = random.choices(GRADES, GRADE_WEIGHTS)[0]
                num_runners = random.randint(7, 14)

                race_id = f"{race_date.strftime('%Y%m%d')}_KW_{race_num:02d}"

                # 出走馬を生成
                odds = _gen_odds(num_runners)
                corners = _gen_corner_positions(num_runners, distance)
                finishes = _gen_finish(num_runners, odds, corners)

                entries = []
                results = []

                for i in range(num_runners):
                    jockey = random.choice(JOCKEYS)
                    trainer = random.choice(TRAINERS)
                    horse_name = _gen_horse_name()
                    horse_weight = random.randint(430, 530)
                    weight_change = random.choice([-6, -4, -2, 0, 0, 0, 2, 4, 6])

                    entries.append({
                        "horse_number": i + 1,
                        "horse_name": horse_name,
                        "post_position": min(i + 1, 8),
                        "jockey_id": jockey[0],
                        "jockey_name": jockey[1],
                        "trainer_id": trainer,
                        "weight_carried": random.choice([54.0, 55.0, 56.0, 57.0]),
                        "horse_weight": horse_weight,
                        "horse_weight_change": weight_change,
                        "odds_win": odds[i],
                        "popularity": i + 1,  # オッズ順 = 人気順
                    })

                    results.append({
                        "horse_number": i + 1,
                        "finish_position": finishes[i],
                        "finish_time": _gen_finish_time(distance, finishes[i], num_runners),
                        "last_3f": _gen_last_3f(finishes[i], num_runners),
                        "corner_positions": corners[i],
                    })

                races.append({
                    "race_id": race_id,
                    "race_date": race_date.isoformat(),
                    "race_number": race_num,
                    "distance": distance,
                    "track_condition": day_condition,
                    "grade": grade,
                    "num_runners": num_runners,
                    "entries": entries,
                    "results": results,
                })

    return {"races": races}


if __name__ == "__main__":
    data = generate_kawasaki_year(2025)
    out = Path(__file__).parent.parent / "data" / "raw" / "sample_races.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(data['races'])} races → {out}")

    # 集計
    distances = {}
    grades = {}
    conditions = {}
    total_horses = 0
    for r in data["races"]:
        distances[r["distance"]] = distances.get(r["distance"], 0) + 1
        grades[r["grade"]] = grades.get(r["grade"], 0) + 1
        conditions[r["track_condition"]] = conditions.get(r["track_condition"], 0) + 1
        total_horses += r["num_runners"]

    print(f"Total horses: {total_horses}")
    print(f"Distances: {dict(sorted(distances.items()))}")
    print(f"Grades: {dict(sorted(grades.items()))}")
    print(f"Conditions: {conditions}")
