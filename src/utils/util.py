"""General utility helpers for rank tier conversions."""

from typing import Optional, Tuple

# Ordered from lowest to highest skill; used to derive rank numbers.
_TIERS_WITH_DIVISIONS = (
    "iron",
    "bronze",
    "silver",
    "gold",
    "plat",
    "emerald",
    "diamond",
)

# Lowest (IV) to highest (I) division ordering keeps rank numbers increasing with skill.
_DIVISION_ORDER = ("IV", "III", "II", "I")

_ORDERED_RANKS = [
    (tier, division)
    for tier in _TIERS_WITH_DIVISIONS
    for division in _DIVISION_ORDER
]
_ORDERED_RANKS.extend(
    [
        ("master", None),
        ("grandmaster", None),
        ("challenger", None),
    ]
)

_VALID_TIERS = {tier for tier, _ in _ORDERED_RANKS}
_TIER_RANK_TO_NUM = {
    (tier, division): index for index, (tier, division) in enumerate(_ORDERED_RANKS)
}


def tier_rank_to_rank_num(tier: str, rank: Optional[str] = None) -> int:
    """Convert a (tier, rank) pair to its numeric ordering."""
    if not tier:
        raise ValueError("tier must be provided")
    normalized_tier = tier.strip().lower()

    if normalized_tier not in _VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'")

    normalized_rank: Optional[str]
    if normalized_tier in _TIERS_WITH_DIVISIONS:
        if not rank:
            raise ValueError(f"Tier '{tier}' requires a rank value")
        normalized_rank = rank.strip().upper()
        if normalized_rank not in _DIVISION_ORDER:
            raise ValueError(f"Unknown rank '{rank}' for tier '{tier}'")
    else:
        normalized_rank = None
        if rank:
            normalized_rank_candidate = rank.strip().upper()
            if normalized_rank_candidate and normalized_rank_candidate != "I":
                raise ValueError(
                    f"Tier '{tier}' does not use ranks, received '{rank}'"
                )

    key = (normalized_tier, normalized_rank)
    if key not in _TIER_RANK_TO_NUM:
        raise ValueError(f"Unsupported tier/rank combination: tier='{tier}', rank='{rank}'")
    return _TIER_RANK_TO_NUM[key]


def rank_num_to_tier_rank(rank_num: int) -> Tuple[str, Optional[str]]:
    """Return the (tier, rank) tuple for a given numeric rank."""
    if not isinstance(rank_num, int):
        raise TypeError("rank_num must be an integer")
    if rank_num < 0 or rank_num >= len(_ORDERED_RANKS):
        raise ValueError(f"rank_num must be between 0 and {len(_ORDERED_RANKS) - 1}")

    tier, rank = _ORDERED_RANKS[rank_num]
    return tier, rank
