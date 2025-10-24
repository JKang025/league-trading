"""Minimal Riot API wrapper for the endpoints used in this project."""

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

import requests
from dotenv import load_dotenv

from src.utils.util import Rank

load_dotenv()


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://developer.riotgames.com",
}

match_v5_limiter = RequestRate(200, Duration.SECOND)
limiter = Limiter(match_v5_limiter)

def _required(container: dict[str, Any], key: str, context: str) -> Any:
    """Fetch a required key from a mapping, raising ValueError when absent or falsy."""
    try:
        value = container[key]
    except KeyError as exc:
        raise ValueError(f"{context!s} missing required field '{key}'") from exc
    if value in (None, ""):
        raise ValueError(f"{context!s} field '{key}' is empty")
    return value


@dataclass(frozen=True)
class MatchParticipant:
    """Represents an individual participant within a match."""

    puuid: str
    champion: str | None
    individual_position: str | None
    team_position: str | None
    team_id: int | None
    win: bool | None
    rank_num: Rank | None

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "MatchParticipant":
        """Create a participant object from a raw Riot API participant payload."""
        try:
            puuid = payload["puuid"]

        except KeyError as exc:
            raise ValueError("MatchParticipant payload missing required field 'puuid'") from exc

        champion_name = payload.get("championName")
        if not champion_name:
            # Older data sets sometimes only provide championId; keep as string for readability.
            try:
                champion_id = payload["championId"]
            except KeyError as exc:
                raise ValueError(
                    "MatchParticipant payload missing both 'championName' and 'championId'"
                ) from exc
            champion_name = str(champion_id)  # TODO

        win_val = payload.get("win")
        if isinstance(win_val, str):
            win_val = win_val.lower() == "true"
        elif win_val is None:
            win_val = None
        try:
            return cls(
                puuid=puuid,
                champion=champion_name,
                individual_position=payload["individualPosition"],
                team_position=payload["teamPosition"],
                team_id=payload["teamId"],
                win=win_val,
            )
        except KeyError as e:
            raise ValueError("MatchParticipant missing fields", e)


@dataclass(frozen=True)
class Match:
    """Represents a match and relevant metadata."""

    match_id: str
    game_creation: int | None
    game_duration: int | None
    game_end_timestamp: int | None
    game_mode: str | None
    game_start_timestamp: int | None
    game_type: str | None
    game_version: str | None
    participants: Sequence[MatchParticipant]

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Match":
        """Parse a Riot Match-V5 response body into a Match object."""
        try:
            metadata = payload["metadata"]
        except KeyError as exc:
            raise ValueError("Match payload missing required field 'metadata'") from exc
        try:
            info = payload["info"]
        except KeyError as exc:
            raise ValueError("Match payload missing required field 'info'") from exc

        try:
            participants_payload = info["participants"]
        except KeyError as exc:
            raise ValueError("Match payload missing required field 'info.participants'") from exc
        if not isinstance(participants_payload, (list, tuple)):
            raise ValueError("Match payload field 'info.participants' must be a list or tuple")

        participants = tuple(
            MatchParticipant.from_json(participant) for participant in participants_payload
        )
        try:
            return cls(
                match_id=_required(metadata, "matchId", "metadata"),
                game_creation=info["gameCreation"],
                game_duration=info["gameDuration"],
                game_end_timestamp=info["gameEndTimestamp"],
                game_mode=info["gameMode"],
                game_start_timestamp=info["gameStartTimestamp"],
                game_type=info["gameType"],
                game_version=info["gameVersion"],
                participants=participants,
            )
        except KeyError as e:
            raise ValueError("Match missing fields", e)


@dataclass
class League:
    """Subset of a ranked league with the players' PUUIDs."""

    players: list[str]
    tier: str
    rank: str | None = None

    @classmethod
    def from_masterplus_json(cls, payload: dict[str, Any]) -> "League":
        """Parse a Master/Grandmaster/Challenger league response into a League."""
        tier = _required(payload, "tier", "league")

        entries_raw = _required(payload, "entries", "league")
        if not isinstance(entries_raw, (list, tuple)):
            raise ValueError("league field 'entries' must be a list")

        players: list[str] = []
        for index, entry in enumerate(entries_raw):
            if not isinstance(entry, dict):
                raise ValueError(f"league entries[{index}] must be an object")
            try:
                puuid = entry["puuid"]
            except KeyError as exc:
                raise ValueError(f"league entries[{index}] missing required field 'puuid'") from exc
            if not puuid:
                raise ValueError(f"league entries[{index}] field 'puuid' is empty")
            players.append(puuid)

        return cls(players=players, tier=tier, rank=None)

    @classmethod
    def from_belowmaster_json(cls, payload: Sequence[dict[str, Any]]) -> "League":
        """Parse a Diamond and below league entry list into a League."""
        if not isinstance(payload, (list, tuple)):
            raise ValueError("below-master league payload must be a list")
        if not payload:
            raise ValueError("below-master league payload is empty")

        players: list[str] = []
        tier = _required(payload[0], "tier", "entries[0]")
        rank = _required(payload[0], "rank", "entries[0]")

        for index, entry in enumerate(payload):
            if not isinstance(entry, dict):
                raise ValueError(f"entries[{index}] must be an object")

            entry_tier = _required(entry, "tier", f"entries[{index}]")
            if entry_tier != tier:
                raise ValueError(f"entries[{index}] tier '{entry_tier}' does not match '{tier}'")

            entry_rank = _required(entry, "rank", f"entries[{index}]")
            if entry_rank != rank:
                raise ValueError(f"entries[{index}] rank '{entry_rank}' does not match '{rank}'")

            puuid = _required(entry, "puuid", f"entries[{index}]")
            players.append(puuid)

        return cls(players=players, tier=tier, rank=rank)


class RiotAPIError(RuntimeError):
    """Raised when a Riot API request fails."""

    def __init__(self, url: str, status_code: int, payload: Any) -> None:
        super().__init__(f"Riot API request to {url} failed with status {status_code}")
        self.url = url
        self.status_code = status_code
        self.payload = payload


class RiotAPI:
    """Very small helper for the needed Riot endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: int = 10,
        session: requests.Session | None = None,
    ) -> None:
        token = api_key or os.getenv("RIOT_API_KEY")
        if not token:
            raise ValueError("Missing Riot API key. Pass api_key or set RIOT_API_KEY.")

        self._token = token
        self._timeout = timeout
        self._session = session or requests.Session()

    def get_league_entries(
        self,
        queue: str = "RANKED_SOLO_5x5",
        tier: str = "DIAMOND",
        division: str = "I",
        *,
        page: int | None = None,
        platform: str,
    ) -> Iterable[dict[str, Any]]:
        url = f"{self._platform_host(platform)}/lol/league/v4/entries/{queue}/{tier}/{division}"
        params = {"page": page} if page is not None else None
        return self._get(url, params=params)

    def get_match_ids_by_puuid(
        self,
        puuid: str,
        *,
        region: str = "americas",
        start_time: int | None = None,
        end_time: int | None = None,
        queue: int | None = 420,  # sr ranked solo
        match_type: str | None = "ranked",
        start: int | None = None,
        count: int | None = None,
    ) -> Iterable[str]:
        url = f"{self._region_host(region)}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params: dict[str, Any] = {}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if queue is not None:
            params["queue"] = queue
        if match_type is not None:
            params["type"] = match_type
        if start is not None:
            params["start"] = start
        if count is not None:
            params["count"] = count
        limiter.aquire("get_match_ids_by_puuid")
        return self._get(url, params=params or None)

    def get_match(self, match_id: str, *, region: str = "americas") -> dict[str, Any]:
        url = f"{self._region_host(region)}/lol/match/v5/matches/{match_id}"
        print(url)
        limiter.aquire("get_match")
        return self._get(url)

    def get_challenger_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/challengerleagues/by-queue/{queue}"
        return self._get(url)

    def get_grandmaster_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/grandmasterleagues/by-queue/{queue}"
        return self._get(url)

    def get_master_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/masterleagues/by-queue/{queue}"
        return self._get(url)

    def route_by_rank_masterplus(
        self,
        platform: str,
        rank: Rank,
        queue: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any]:
        """Get league data for a specific rank, routing to the appropriate endpoint."""

        # Route to appropriate method based on tier
        if rank == Rank.challenger:
            return self.get_challenger_league(queue=queue, platform=platform)
        elif rank == Rank.grandmaster:
            return self.get_grandmaster_league(queue=queue, platform=platform)
        elif rank == Rank.master:
            return self.get_master_league(queue=queue, platform=platform)
        else:
            raise ValueError(f"Unsupported rank: {rank}")

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        print(url)
        response = self._session.get(
            url,
            params=params,
            headers=self._headers(),
            timeout=self._timeout,
        )
        if not response.ok:
            raise RiotAPIError(
                url=url,
                status_code=response.status_code,
                payload=self._safe_json(response),
            )
        return self._safe_json(response)

    def _headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        headers["X-Riot-Token"] = self._token
        return headers

    @staticmethod
    def _platform_host(platform: str) -> str:
        # BR1, EUN1, EUW1, JP1, KR, LA1, LA2, ME1, NA1, OC1, RU, SG2, TR1, TW2, VN2
        # Use these platform routing values for everything other than match endpoints (i.e., league).
        return f"https://{platform.lower()}.api.riotgames.com"

    @staticmethod
    def _region_host(region: str) -> str:
        # There is americas (NA, BR, LAN and LAS), asia (KR, JP), sea (OCE, SG2, TW2 and VN2), europe (EUNE, EUW, ME1, TR and RU)
        # ONLY for matches API.
        return f"https://{region.lower()}.api.riotgames.com"

    @staticmethod
    def _safe_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text


__all__ = ["Match", "MatchParticipant", "League", "RiotAPI", "RiotAPIError"]


def _main() -> None:
    """Fetch and print representative league payloads as League instances."""
    api = RiotAPI()

    # # Test the new get_league function

    # # Test with different ranks
    # print("Testing get_league function:")

    # # Test Challenger
    # try:
    #     challenger_data = api.get_league(platform="NA1", rank=Rank.CHALLENGER)
    #     print("Challenger league data retrieved successfully")
    # except Exception as e:
    #     print(f"Error getting Challenger league: {e}")

    # # Test Diamond I
    # try:
    #     diamond_data = api.get_league(platform="NA1", rank=Rank.DIAMOND_I)
    #     print("Diamond I league data retrieved successfully")
    # except Exception as e:
    #     print(f"Error getting Diamond I league: {e}")

    # # Test Gold IV
    # try:
    #     gold_data = api.get_league(platform="NA1", rank=Rank.GOLD_IV)
    #     print("Gold IV league data retrieved successfully")
    # except Exception as e:
    #     print(f"Error getting Gold IV league: {e}")

    # # Original test code
    # grandmaster_payload = api.get_grandmaster_league(platform="na1")
    # grandmaster_league = League.from_masterplus_json(grandmaster_payload)
    # print("Grandmaster League:", grandmaster_league)

    api = RiotAPI()
    puuid = "ztT2H_3CFSD_wAuniuqzff1CNu2fpNRvKpHguidxsyJammiKxA2yP14K7nGnxr-gB0obLNK8eMsM9Q"
    matches = api.get_match_ids_by_puuid(puuid, region="americas")
    print(matches)
    match_json = api.get_match(matches[0], region="americas")
    print(match_json)

    # print(
    #     api.get_match_ids_by_puuid(
    #         "_VW97HmRBLrC0wD6GbMxTXrBsixlAP02INmRCJr2g6MNseBFah-gXWIOBit1_PtDVFknKnocrbWozQ"
    #     )
    # )


if __name__ == "__main__":
    _main()
