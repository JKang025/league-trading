import math
import asyncio

from src.utils.util import Rank, PLATFORM_TO_REGION
from src.data.riot_api import RiotAPI, Match
from src.data.duckdb import MatchDatabase


database = MatchDatabase()

def query_matches(
    platform: str,
    rank: Rank,
    start_time: str,
    end_time: str,
    num_matches: int,
):
    if rank in [Rank.CHALLENGER, Rank.GRANDMASTER, Rank.MASTER]:
        # league = api.get_league(platform=platform, rank=rank)
        # players = deque(league.players)
        # players1 = deque()
        # num_players = len(players)

        
        # matches_per_player = math.ceil(num_matches / num_players) # starting heuristic for how many matches to get for each player
        # matches_processed = 0
        # while matches_processed < num_matches and len(players) > 0:
        #     player = players.pop()
        #     matches = api.get_match_ids_by_puuid(
        #         player,
        #         region=PLATFORM_TO_REGION[platform],
        #         start_time=start_time,
        #         end_time=end_time,
        #         start=0,
        #         count=matches_per_player,
        #     )
        #     matches_processed += len(matches) # not nessesarily true, need to check with if match is already in duckdb 
        #                                       # and if match is already processed from some other player

        #     if len(matches) == matches_per_player:
        #         players1.appendleft(player)
            
        #     if len(players) == 0:
        #         players = players1
        #         players1 = deque()
        #         matches_per_player = math.ceil((num_matches - matches_processed) / len(players))
        pass

#TODO: rate limiting logic 
    
def gather_matches(    
    platform: str,
    start_time: str,
    end_time: str,
    target_num_matches: int,
    players: list[str],
    )->int:
    api = RiotAPI()
    match_ids: set[str] = set()

    matches_per_player = max(math.ceil(target_num_matches / len(players)), 2)
    batch_size_match_ids_by_puuid = int(200 * 0.1) # 200 req / s * 0.1 s = 60 batch_size 
                                # rough estimate, estimate towards smaller flight time

    async def fetch_for_player(puuid: str) -> None:
        ids = await asyncio.to_thread(
            api.get_match_ids_by_puuid,
            puuid,
            region=PLATFORM_TO_REGION[platform],
            start_time=start_time,
            end_time=end_time,
            start=0,
            count=matches_per_player,
        )
        if ids:
            match_ids.update(ids)

    async def fetch_all() -> None:
        for i in range(0, len(players), batch_size_match_ids_by_puuid):
            batch = players[i:i + batch_size_match_ids_by_puuid]
            tasks = [asyncio.create_task(fetch_for_player(puuid)) for puuid in batch]
            await asyncio.gather(*tasks, return_exceptions=False)

    # Fetch all match IDs from players
    asyncio.run(fetch_all())
    
    new_match_ids = database.get_only_new_match_ids(match_ids)
    
    # Fetch match details for each new match ID
    matches: list[Match] = []

    batch_size_match_details = int(200 * 0.1) # 200 req / s * 0.1 s = 60 batch_size 
                                # rough estimate, estimate towards smaller flight time
    async def fetch_match_details(match_id: str) -> None:
        match_data = await asyncio.to_thread(
            api.get_match,
            match_id,
            region=PLATFORM_TO_REGION[platform]
        )
        if match_data:
            match_obj = Match.from_json(match_data)
            matches.append(match_obj)

    async def fetch_all_matches() -> None:
        for i in range(0, len(new_match_ids), batch_size_match_details):
            batch = list(new_match_ids)[i:i + batch_size_match_details]
            tasks = [asyncio.create_task(fetch_match_details(match_id)) for match_id in batch]
            await asyncio.gather(*tasks, return_exceptions=False)

    # Fetch all match details
    asyncio.run(fetch_all_matches())
    
    # Insert match details into database
    sucsessful_inserts = 0
    database.upsert_many(matches)
    
    return sucsessful_inserts

