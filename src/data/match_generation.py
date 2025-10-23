import math
import asyncio

from src.utils.util import Rank, PLATFORM_TO_REGION
from src.data.riot_api import RiotAPI, League


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

# controller logic that determines whether to run again or not 
    # get match ids
        # verify that it wasn't already processed from some other player

    # verify match ids are not already in duckdb
    # add to duckdb
    # return number of matches added

    #IDEA: (req / s ) * (time in flight) = batch_size of async 
    # 200 req / s * 0.3 s = 60 batch_size ROUGH ESTIMATE FOR BATCH SIZE
    #IDEA: we can do async for getting matchids and async for getting matches, 
    # but lets make the pipline itself sync for now, i,e get matchid first, 
    # # hen verift against db, then query matches, then insert
    
def gather_matches(    
    platform: str,
    start_time: str,
    end_time: str,
    target_num_matches: int,
    league: League,
    )->int:
    players = league.players
    matches_per_player = max(math.ceil(target_num_matches / len(players)), 2)
    api = RiotAPI()

    match_ids: set[str] = set()

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
        tasks = [asyncio.create_task(fetch_for_player(puuid)) for puuid in players]
        await asyncio.gather(*tasks, return_exceptions=False)

    asyncio.run(fetch_all())

    # TODO: verify match ids are not already in duckdb, then insert and return number added
    return 0

