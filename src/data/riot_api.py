"""Minimal Riot API wrapper for the endpoints used in this project."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence
import os
from dotenv import load_dotenv
load_dotenv()
import requests


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


def _required(container: Dict[str, Any], key: str, context: str) -> Any:
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
    champion: Optional[str]
    individual_position: Optional[str]
    team_position: Optional[str]
    team_id: Optional[int]
    win: Optional[bool]
    rank_num: Optional[bool]

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "MatchParticipant":
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
            champion_name = str(champion_id)

        return cls(
            puuid=puuid,
            champion=champion_name,
            individual_position=payload.get("individualPosition"),
            team_position=payload.get("teamPosition"),
            team_id=payload.get("teamId"),
            win=(payload.get("win") == "true"),
        )


@dataclass(frozen=True)
class Match:
    """Represents a match and relevant metadata."""

    match_id: str
    game_creation: Optional[int]
    game_duration: Optional[int]
    game_end_timestamp: Optional[int]
    game_mode: Optional[str]
    game_start_timestamp: Optional[int]
    game_type: Optional[str]
    game_version: Optional[str]
    participants: Sequence[MatchParticipant]

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "Match":
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
            MatchParticipant.from_json(participant)
            for participant in participants_payload
        )

        return cls(
            match_id=_required(metadata, "matchId", "metadata"),
            game_creation=info.get("gameCreation"),
            game_duration=info.get("gameDuration"),
            game_end_timestamp=info.get("gameEndTimestamp"),
            game_mode=info.get("gameMode"),
            game_start_timestamp=info.get("gameStartTimestamp"),
            game_type=info.get("gameType"),
            game_version=info.get("gameVersion"),
            participants=participants,
        )


@dataclass
class League:
    """Subset of a ranked league with the players' PUUIDs."""

    players: List[str]
    tier: str
    rank: Optional[str] = None

    @classmethod
    def from_masterplus_json(cls, payload: Dict[str, Any]) -> "League":
        """Parse a Master/Grandmaster/Challenger league response into a League."""
        tier = _required(payload, "tier", "league")

        entries_raw = _required(payload, "entries", "league")
        if not isinstance(entries_raw, (list, tuple)):
            raise ValueError("league field 'entries' must be a list")

        players: List[str] = []
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
    def from_belowmaster_json(cls, payload: Sequence[Dict[str, Any]]) -> "League":
        """Parse a Diamond and below league entry list into a League."""
        if not isinstance(payload, (list, tuple)):
            raise ValueError("below-master league payload must be a list")
        if not payload:
            raise ValueError("below-master league payload is empty")

        players: List[str] = []
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
        api_key: Optional[str] = None,
        *,
        timeout: int = 10,
        session: Optional[requests.Session] = None,
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
        page: Optional[int] = None,
        platform: str,
    ) -> Iterable[Dict[str, Any]]:
        url = f"{self._platform_host(platform)}/lol/league/v4/entries/{queue}/{tier}/{division}"
        params = {"page": page} if page is not None else None
        return self._get(url, params=params)

    def get_match_ids_by_puuid(
        self,
        puuid: str,
        *,
        region: str = "americas",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        queue: Optional[int] = None,
        match_type: Optional[str] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
    ) -> Iterable[str]:
        url = f"{self._region_host(region)}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params: Dict[str, Any] = {}
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
        return self._get(url, params=params or None)

    def get_match(self, match_id: str, *, region: str = "americas") -> Dict[str, Any]:
        url = f"{self._region_host(region)}/lol/match/v5/matches/{match_id}"
        print(url)
        return self._get(url)

    def get_challenger_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> Dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/challengerleagues/by-queue/{queue}"
        return self._get(url)

    def get_grandmaster_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> Dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/grandmasterleagues/by-queue/{queue}"
        return self._get(url)

    def get_master_league(
        self,
        queue: str = "RANKED_SOLO_5x5",
        *,
        platform: str = "NA1",
    ) -> Dict[str, Any]:
        url = f"{self._platform_host(platform)}/lol/league/v4/masterleagues/by-queue/{queue}"
        return self._get(url)

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
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

    def _headers(self) -> Dict[str, str]:
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

    # league_entries_payload = list(api.get_league_entries(platform="na1"))
    # below_master_league = League.from_belowmaster_json(league_entries_payload)
    # print("Below Master League:", below_master_league)

    # challenger_payload = api.get_challenger_league(platform="na1")
    # challenger_league = League.from_masterplus_json(challenger_payload)
    # print("Challenger League:", challenger_league)

    # grandmaster_payload = api.get_grandmaster_league(platform="na1")
    # grandmaster_league = League.from_masterplus_json(grandmaster_payload)
    # print("Grandmaster League:", grandmaster_league)

    # master_payload = api.get_master_league(platform="na1")
    # master_league = League.from_masterplus_json(master_payload)
    # print("Master League:", master_league)

    api = RiotAPI()
    puuid = "PKDb1Hr2KqfmEKLuPeq6rA_uq9K3oKpjo6UX6aH2hd332uVN4phfnomMXTwPRUMRulm_XQ04Xj-f6g"
    matches = api.get_match_ids_by_puuid(puuid, region="americas")
    print(matches)


if __name__ == "__main__":
    _main()
