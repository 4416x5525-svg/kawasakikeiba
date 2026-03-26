"""半構造化コメント（kawasaki_keiba.race_video）。

契約:
  - 許可される template_id は COMMENT_TEMPLATE_FIELDS のキーのみ
  - 1 レコードの並び順は COMMENT_TEMPLATE_FIELDS[template_id] の列順（固定）
  - 値は str。空文字のキーは to_ordered_parts / to_line では省略
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

COMMENT_TEMPLATE_FIELDS: Final[dict[str, tuple[str, ...]]] = {
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

REGISTERED_TEMPLATE_IDS: frozenset[str] = frozenset(COMMENT_TEMPLATE_FIELDS)


class TemplateError(ValueError):
    """未登録 template_id または必須キー欠落。"""


@dataclass(frozen=True)
class SemiStructuredComment:
    """template_id とキー→値（順序はテンプレート定義に従う）。"""

    template_id: str
    fields: dict[str, str]

    def to_ordered_parts(self) -> tuple[tuple[str, str], ...]:
        keys = COMMENT_TEMPLATE_FIELDS.get(self.template_id)
        if keys is None:
            msg = f"unknown template_id: {self.template_id!r}"
            raise TemplateError(msg)
        return tuple(
            (k, self.fields[k]) for k in keys if k in self.fields and self.fields[k] != ""
        )

    def to_line(self, *, sep: str = " | ") -> str:
        parts = self.to_ordered_parts()
        return sep.join(f"{k}={v}" for k, v in parts)


def render_semi_comment(
    template_id: str,
    fields: Mapping[str, str],
    *,
    required_keys: tuple[str, ...] | None = None,
) -> SemiStructuredComment:
    """REGISTERED_TEMPLATE_IDS に含まれる template_id のみ受け付ける。"""
    if template_id not in COMMENT_TEMPLATE_FIELDS:
        msg = f"unknown template_id: {template_id!r}"
        raise TemplateError(msg)
    data = dict(fields)
    if required_keys is not None:
        missing = [k for k in required_keys if not data.get(k)]
        if missing:
            msg = f"missing required keys: {missing}"
            raise TemplateError(msg)
    return SemiStructuredComment(template_id=template_id, fields=data)
