"""レース映像コメント用の半構造化テンプレート（記録形式の固定）。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# テンプレート ID → 出力に並べるフィールドキー（順序固定）
COMMENT_TEMPLATE_FIELDS: dict[str, tuple[str, ...]] = {
    "race_review_v1": (
        "main_tags",
        "aux_tags",
        "position_summary",
        "pace_summary",
        "linear_summary",
        "outcome_summary",
    ),
    "race_review_minimal": ("main_tags", "aux_tags"),
}


class TemplateError(ValueError):
    """未知の template_id または必須キー欠落。"""


@dataclass(frozen=True)
class SemiStructuredComment:
    """人間可読1行と、機械向けフィールドを両方保持する。"""

    template_id: str
    fields: dict[str, str]

    def to_ordered_parts(self) -> tuple[tuple[str, str], ...]:
        keys = COMMENT_TEMPLATE_FIELDS.get(self.template_id)
        if keys is None:
            msg = f"unknown template_id: {self.template_id!r}"
            raise TemplateError(msg)
        return tuple((k, self.fields[k]) for k in keys if k in self.fields and self.fields[k] != "")

    def to_line(self, *, sep: str = " | ") -> str:
        parts = self.to_ordered_parts()
        return sep.join(f"{k}={v}" for k, v in parts)


def render_semi_comment(
    template_id: str,
    fields: Mapping[str, str],
    *,
    required_keys: tuple[str, ...] | None = None,
) -> SemiStructuredComment:
    """テンプレートに沿った SemiStructuredComment を構築する。"""
    if template_id not in COMMENT_TEMPLATE_FIELDS:
        msg = f"unknown template_id: {template_id!r}"
        raise TemplateError(msg)
    data = dict(fields)
    req = required_keys
    if req is not None:
        missing = [k for k in req if not data.get(k)]
        if missing:
            msg = f"missing required keys: {missing}"
            raise TemplateError(msg)
    return SemiStructuredComment(template_id=template_id, fields=data)
