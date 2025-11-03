import math
import asyncio

from src.utils.util import Rank, PLATFORM_TO_REGION, date_string_to_iso_start_of_day, iso_to_timestamp_s
from src.data.riot_api import RiotAPI, Match, League
from src.data.duckdb import MatchDatabase, QueryProgressTracker



match_database = MatchDatabase()
query_progress_tracker = QueryProgressTracker()

def query_matches(
    platform: str,
    rank: Rank,
    start_time: str,
    end_time: str,
    num_matches: int,
):
    processed_matches = 0
    iterations = 0
    rank_page_start_index = 1

    MAX_PAGE_INDEX = 10 # random index, just in case overflow (unlucky though)
    MAX_ITERATIONS = 10 # random iterations, just in case overflow (unlucky though)

    while processed_matches < num_matches and iterations < MAX_ITERATIONS:
        iterations += 1

        if rank in [Rank.CHALLENGER, Rank.GRANDMASTER, Rank.MASTER]:
            league = api.get_league(platform=platform, rank=rank)
            players = league.players
        else:
            league = api.get_league(platform=platform, rank=rank, page=rank_page_start_index)
            rank_page_start_index = (rank_page_start_index + 1) % MAX_PAGE_INDEX
            players = league.players

        processed_matches += gather_matches(platform, start_time, end_time, num_matches, players, rank)
    return processed_matches


#TODO: rate limiting logic 
    
def gather_matches(    
    platform: str,
    start_time: str,
    end_time: str,
    target_num_matches: int,
    players: list[str],
    rank: Rank,
    )->int:
    api = RiotAPI()
    match_ids: set[str] = set()

    matches_per_player = max(math.ceil(target_num_matches / len(players)), 2)
    batch_size_match_ids_by_puuid = int(200 * 0.1) # 200 req / s * 0.1 s = 60 batch_size 
                                # rough estimate, estimate towards smaller flight time
    batch_size_match_ids_by_puuid = 1

    async def fetch_for_player(puuid: str) -> None:
        try:
            start_index = query_progress_tracker.get_query_start_index(platform, start_time, end_time, puuid)
            # Convert ISO strings to Unix timestamps in seconds for the API
            start_time_s = iso_to_timestamp_s(start_time)
            end_time_s = iso_to_timestamp_s(end_time)
            ids = await asyncio.to_thread(
                api.get_match_ids_by_puuid,
                puuid,
                region=PLATFORM_TO_REGION[platform],
                start_time=start_time_s,
                end_time=end_time_s,
                start=start_index,
                count=matches_per_player,
            )
            query_progress_tracker.update_start_index(platform, start_time, end_time, puuid, start_index + len(ids))
            if ids:
                match_ids.update(ids)
            print(f"Fetched {len(ids)} match IDs for player {puuid}")
        except Exception as e:
            print(f"Error fetching match IDs for player {puuid}: {e}")

    async def fetch_all() -> None:
        for i in range(0, len(players), batch_size_match_ids_by_puuid):
            batch = players[i:i + batch_size_match_ids_by_puuid]
            tasks = [asyncio.create_task(fetch_for_player(puuid)) for puuid in batch]
            await asyncio.gather(*tasks, return_exceptions=False)

    # Fetch all match IDs from players
    asyncio.run(fetch_all())
    
    new_match_ids = match_database.get_only_new_match_ids(match_ids)
    
    # Fetch match details for each new match ID
    matches: list[Match] = []

    batch_size_match_details = int(200 * 0.1) # 200 req / s * 0.1 s = 60 batch_size 
                                # rough estimate, estimate towards smaller flight time
    batch_size_match_details = 1
    async def fetch_match_details(match_id: str) -> None:
        try:
            match_data = await asyncio.to_thread(
                api.get_match,
                match_id,
                region=PLATFORM_TO_REGION[platform]
            )
            if match_data:
                match_obj = Match.from_json(match_data)
                match_obj.set_rank(rank)
                matches.append(match_obj)
            print(f"Fetched match details for match {match_id}")
        except Exception as e:
            print(f"Error fetching match details for match {match_id}: {e}")

    async def fetch_all_matches() -> None:
        for i in range(0, len(new_match_ids), batch_size_match_details):
            batch = list(new_match_ids)[i:i + batch_size_match_details]
            tasks = [asyncio.create_task(fetch_match_details(match_id)) for match_id in batch]
            await asyncio.gather(*tasks, return_exceptions=False)

    # Fetch all match details
    asyncio.run(fetch_all_matches())
    
    # Insert match details into database
    sucsessful_inserts = match_database.upsert_many(matches)
    
    return sucsessful_inserts

if __name__ == "__main__":
    platform = "NA1"
    rank = Rank.CHALLENGER
    api = RiotAPI()
    start_time = date_string_to_iso_start_of_day("2025-10-29")
    end_time = date_string_to_iso_start_of_day("2025-10-30")
    target_num_matches = 100

    sucsessful_matches = query_matches(platform, rank, start_time, end_time, target_num_matches)
    print(sucsessful_matches)