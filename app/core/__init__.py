"""Kern-Logik: Datenmodell, Scores, Formatierung und Datenquellen."""

from .models import Match, TeamStats
from .scoring import gefahr_score, scope_score
from .formatting import format_match
from .mock_data import get_matches

__all__ = [
    "Match",
    "TeamStats",
    "gefahr_score",
    "scope_score",
    "format_match",
    "get_matches",
]
