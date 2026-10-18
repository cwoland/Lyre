import secrets
from typing import Literal


CURSOR_COLORS: Final = (
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#06b6d4",
    "#3b82f6",
    "#8b5cf6",
    "#ec4899",
)


def pick_color_cursor() -> str:
    return secrets.choice(CURSOR_COLORS)
