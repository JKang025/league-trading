"""General utility helpers for rank tier conversions."""

import datetime
from enum import Enum
from typing import Optional, Tuple

PLATFORM_TO_REGION = {
    "NA1": "americas",
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "RU": "europe",
    "ME1": "europe",
    "TR1": "europe",
    "EUN1": "europe",
    "EUW1": "europe",
    "OC1": "sea",
    "SG2": "sea",
    "TW2": "sea",
    "VN2": "sea",
    "JP1": "asia",
    "KR": "asia",
}

class Rank(Enum):
    """Enum representing all individual ranks in League of Legends with numeric values."""

    # Iron ranks (0-3)
    IRON_IV = 0
    IRON_III = 1
    IRON_II = 2
    IRON_I = 3

    # Bronze ranks (4-7)
    BRONZE_IV = 4
    BRONZE_III = 5
    BRONZE_II = 6
    BRONZE_I = 7

    # Silver ranks (8-11)
    SILVER_IV = 8
    SILVER_III = 9
    SILVER_II = 10
    SILVER_I = 11

    # Gold ranks (12-15)
    GOLD_IV = 12
    GOLD_III = 13
    GOLD_II = 14
    GOLD_I = 15

    # Platinum ranks (16-19)
    PLAT_IV = 16
    PLAT_III = 17
    PLAT_II = 18
    PLAT_I = 19

    # Emerald ranks (20-23)
    EMERALD_IV = 20
    EMERALD_III = 21
    EMERALD_II = 22
    EMERALD_I = 23

    # Diamond ranks (24-27)
    DIAMOND_IV = 24
    DIAMOND_III = 25
    DIAMOND_II = 26
    DIAMOND_I = 27

    # Master tier ranks (28-30)
    MASTER = 28
    GRANDMASTER = 29
    CHALLENGER = 30


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
    (tier, division) for tier in _TIERS_WITH_DIVISIONS for division in _DIVISION_ORDER
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
                raise ValueError(f"Tier '{tier}' does not use ranks, received '{rank}'")

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


def tier_rank_to_rank_enum(tier: str, rank: Optional[str] = None) -> Rank:
    """Convert a (tier, rank) pair to its corresponding Rank enum."""
    rank_num = tier_rank_to_rank_num(tier, rank)
    return rank_num_to_rank_enum(rank_num)


def rank_num_to_rank_enum(rank_num: int) -> Rank:
    """Convert a numeric rank to its corresponding Rank enum."""
    # Find the enum member with the matching numeric value
    for rank_enum in Rank:
        if rank_enum.value == rank_num:
            return rank_enum

    raise ValueError(f"No enum found for rank_num={rank_num}")


def rank_enum_to_tier_rank(rank_enum: Rank) -> Tuple[str, Optional[str]]:
    """Convert a Rank enum to its corresponding (tier, rank) tuple."""
    rank_num = rank_enum.value
    return rank_num_to_tier_rank(rank_num)


def rank_enum_to_rank_num(rank_enum: Rank) -> int:
    """Convert a Rank enum to its numeric rank."""
    return rank_enum.value


def timestamp_s_to_iso(timestamp_s: int) -> str:
    """Convert second timestamp to ISO 8601 format."""
    dt = datetime.datetime.fromtimestamp(timestamp_s)
    return dt.isoformat()


def iso_to_timestamp_s(iso_string: str) -> int:
    """Convert ISO 8601 format to second timestamp."""
    dt = datetime.datetime.fromisoformat(iso_string)
    return int(dt.timestamp())


def date_string_to_iso_start_of_day(date_string: str) -> str:
    """Convert a simple date string (YYYY-MM-DD) to ISO 8601 format at start of day."""
    try:
        # Parse the date string
        dt = datetime.datetime.strptime(date_string, "%Y-%m-%d")
        # Return ISO format (start of day - 00:00:00)
        return dt.isoformat()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_string}'. Expected YYYY-MM-DD format.") from e
