import math
from collections import deque

from src.utils.util import Rank, PLATFORM_TO_REGION
from src.data.riot_api import RiotAPI


def query_matches(
    platform: str,
    rank: Rank,
    start_time: str,
    end_time: str,
    num_matches: int,
):
    api = RiotAPI()

    if rank in [Rank.CHALLENGER, Rank.GRANDMASTER, Rank.MASTER]:
        league = api.get_league(platform=platform, rank=rank)
        players = deque(league.players)
        players1 = deque()
        num_players = len(players)

        
        matches_per_player = math.ciel(num_matches / num_players) # starting heuristic for how many matches to get for each player
        matches_processed = 0
        while matches_processed < num_matches and len(players) > 0 and len(players1) > 0:
            player = players.pop()
            matches = api.get_match_ids_by_puuid(
                player,
                region=PLATFORM_TO_REGION[rank],
                start_time=start_time,
                end_time=end_time,
                start=0,
                count=matches_per_player,
            )
            matches_processed += len(matches)

            if len(matches) == matches_per_player:
                players1.appendleft(player)
            
            if len(players) == 0:
                player = players1
                players1 = deque()
                matches_per_player = math.ceil((num_matches - matches_processed) / len(players))
            
        match_ids = 
