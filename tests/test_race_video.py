"""Race Video タグ・コメント・再発度・選定のテスト"""

import pytest

from kawasaki_keiba.race_video.comment_templates import (
    TemplateError,
    render_semi_comment,
)
from kawasaki_keiba.race_video.race_tags import (
    AuxiliaryRaceTag,
    MainRaceTag,
    TagConstraintError,
    race_tag_selection,
)
from kawasaki_keiba.race_video.recurrence import (
    RecurrenceLevel,
    count_main_tag_in_window,
    recurrence_level_for_main_tag,
    recurrence_level_from_hit_count,
)
from kawasaki_keiba.race_video.selection import (
    ReviewCandidate,
    select_race_video_review_targets,
)


class TestRaceTags:
    def test_valid_selection(self):
        sel = race_tag_selection(
            main=(MainRaceTag.POSITION_FRONT, MainRaceTag.WIN_PACE_FIT),
            auxiliary=(AuxiliaryRaceTag.STRONG_FINISH,),
        )
        assert len(sel.main) == 2
        assert len(sel.auxiliary) == 1

    def test_too_many_main_tags(self):
        with pytest.raises(TagConstraintError, match="at most 2"):
            race_tag_selection(
                main=(MainRaceTag.POSITION_FRONT, MainRaceTag.PACE_FAST, MainRaceTag.WIN_POSITION),
            )

    def test_duplicate_main_tags(self):
        with pytest.raises(TagConstraintError, match="duplicates"):
            race_tag_selection(
                main=(MainRaceTag.POSITION_FRONT, MainRaceTag.POSITION_FRONT),
            )

    def test_empty_main_ok(self):
        sel = race_tag_selection(main=())
        assert len(sel.main) == 0


class TestCommentTemplates:
    def test_render_minimal(self):
        comment = render_semi_comment(
            "race_review_minimal",
            {"main_tags": "position_front", "aux_tags": "strong_finish"},
        )
        line = comment.to_line()
        assert "main_tags=position_front" in line
        assert "aux_tags=strong_finish" in line

    def test_unknown_template(self):
        with pytest.raises(TemplateError, match="unknown"):
            render_semi_comment("nonexistent", {})

    def test_required_keys_missing(self):
        with pytest.raises(TemplateError, match="missing required"):
            render_semi_comment(
                "race_review_minimal",
                {"main_tags": "x"},
                required_keys=("main_tags", "aux_tags"),
            )

    def test_empty_fields_skipped(self):
        comment = render_semi_comment(
            "race_review_minimal",
            {"main_tags": "x", "aux_tags": ""},
        )
        parts = comment.to_ordered_parts()
        assert len(parts) == 1


class TestRecurrence:
    def test_low_recurrence(self):
        assert recurrence_level_from_hit_count(0) == RecurrenceLevel.LOW
        assert recurrence_level_from_hit_count(1) == RecurrenceLevel.LOW

    def test_medium_recurrence(self):
        assert recurrence_level_from_hit_count(2) == RecurrenceLevel.MEDIUM

    def test_high_recurrence(self):
        assert recurrence_level_from_hit_count(3) == RecurrenceLevel.HIGH

    def test_negative_hits(self):
        with pytest.raises(ValueError, match="non-negative"):
            recurrence_level_from_hit_count(-1)

    def test_count_in_window(self):
        history = [MainRaceTag.LOSS_PACE, None, MainRaceTag.LOSS_PACE, MainRaceTag.WIN_POSITION]
        count = count_main_tag_in_window(MainRaceTag.LOSS_PACE, history, window=3)
        assert count == 1  # only the 3rd element in last 3

    def test_recurrence_for_tag(self):
        history = [
            MainRaceTag.LOSS_BLOCKED,
            MainRaceTag.LOSS_BLOCKED,
            MainRaceTag.LOSS_BLOCKED,
        ]
        level = recurrence_level_for_main_tag(MainRaceTag.LOSS_BLOCKED, history)
        assert level == RecurrenceLevel.HIGH


class TestSelection:
    def test_popularity_based(self):
        candidates = [
            ReviewCandidate(horse_id="H3", horse_number=3, popularity_rank=3),
            ReviewCandidate(horse_id="H1", horse_number=1, popularity_rank=1),
            ReviewCandidate(horse_id="H2", horse_number=2, popularity_rank=2),
        ]
        result = select_race_video_review_targets(candidates, max_horses=2)
        assert result == ("H1", "H2")

    def test_no_popularity(self):
        candidates = [
            ReviewCandidate(horse_id="H5", horse_number=5),
            ReviewCandidate(horse_id="H2", horse_number=2),
        ]
        result = select_race_video_review_targets(candidates, max_horses=4)
        assert result[0] == "H2"  # lower horse_number first

    def test_max_horses_limit(self):
        candidates = [
            ReviewCandidate(horse_id=f"H{i}", horse_number=i, popularity_rank=i)
            for i in range(1, 10)
        ]
        result = select_race_video_review_targets(candidates, max_horses=3)
        assert len(result) == 3

    def test_max_horses_validation(self):
        with pytest.raises(ValueError, match="max_horses"):
            select_race_video_review_targets([], max_horses=0)
