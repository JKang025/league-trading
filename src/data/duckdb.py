import duckdb
from typing import Iterable
import sys
from pathlib import Path
from src.data.riot_api import Match  


class MatchDatabase:
    """Database manager for League of Legends match data."""
    
    def __init__(self, db_path: str = "data/match_data/matches.duckdb"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.con = duckdb.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Create tables and indexes if they don't exist."""
        self.con.execute("""CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            game_creation BIGINT,
            game_duration BIGINT,
            game_end_timestamp BIGINT,
            game_mode TEXT,
            game_start_timestamp BIGINT,
            game_type TEXT,
            game_version TEXT
        );""")
        self.con.execute("""CREATE TABLE IF NOT EXISTS participants (
            match_id TEXT,
            puuid TEXT,
            champion TEXT,
            individual_position TEXT,
            team_position TEXT,
            team_id INTEGER,
            win BOOLEAN,
            rank_num INTEGER,
            PRIMARY KEY (match_id, puuid),
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        );""")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants(puuid);")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_participants_champion ON participants(champion);")
    
    def upsert_match(self, m: Match):
        """Upsert a single match into the database."""
        # Insert the match; ignore if it already exists
        self.con.execute("""
            INSERT INTO matches (
                match_id, game_creation, game_duration, game_end_timestamp,
                game_mode, game_start_timestamp, game_type, game_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO NOTHING
        """, [
            m.match_id, m.game_creation, m.game_duration, m.game_end_timestamp,
            m.game_mode, m.game_start_timestamp, m.game_type, m.game_version
        ])

        # Insert participants; ignore duplicates
        rows = []
        for p in m.participants:
            rank_num = getattr(p, "rank_num", None)
            # Convert Rank enum to its integer value for DuckDB
            if rank_num is not None and hasattr(rank_num, 'value'):
                rank_num = rank_num.value
            rows.append([
                m.match_id,
                p.puuid,
                p.champion,
                p.individual_position,
                p.team_position,
                p.team_id,
                p.win,
                rank_num
            ])
        self.con.executemany("""
            INSERT INTO participants (
              match_id, puuid, champion, individual_position, team_position,
              team_id, win, rank_num
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, puuid) DO NOTHING
        """, rows)

    def upsert_many(self, matches: Iterable[Match]) -> int:
        """
        Upsert multiple matches into the database.
        
        Args:
            matches: Iterable of Match objects to upsert
            
        Returns:
            Number of matches successfully upserted
        """
        count = 0
        with self.con:  # single transaction
            for m in matches:
                self.upsert_match(m)
                count += 1
        return count

    def get_only_new_match_ids(self, match_ids: set[str]) -> set[str]:
        """
        Check which match_ids are NOT in the database.
        
        Args:
            match_ids: Set of match_ids to check
            
        Returns:
            Set of match_ids that are NOT in the database (i.e., new match_ids)
        """
        if not match_ids:
            return set()
        
        match_ids_list = list(match_ids)
        placeholders = ','.join(['?' for _ in match_ids_list])
        
        query = f"""
        SELECT match_id 
        FROM matches 
        WHERE match_id IN ({placeholders})
        """
        
        result = self.con.execute(query, match_ids_list).fetchall()
        existing_ids = {row[0] for row in result}
        
        return match_ids - existing_ids
    
    def clear_all_data(self) -> None:
        """
        Remove all data from the database.
        
        This will delete all rows from both the participants and matches tables.
        The tables and indexes will remain intact.
        """
        # Delete participants first due to foreign key constraint
        self.con.execute("DELETE FROM participants")
        self.con.execute("DELETE FROM matches")
    
    def close(self):
        """Close the database connection."""
        self.con.close()
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting context."""
        self.close()


class QueryProgressTracker:
    """Tracks query progress for match ID fetching by player, platform, and time range."""
    
    def __init__(self, db_path: str = "data/match_data/query_progress.duckdb"):
        """
        Initialize query progress tracker.
        
        Args:
            db_path: Path to the DuckDB database file (should match MatchDatabase)
        """
        self.db_path = db_path
        self.con = duckdb.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Create query_progress table if it doesn't exist."""
        self.con.execute("""CREATE TABLE IF NOT EXISTS query_progress (
            platform TEXT,
            start_time TEXT,
            end_time TEXT,
            puuid TEXT,
            last_start_index INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (platform, start_time, end_time, puuid)
        );""")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_query_progress_lookup ON query_progress(platform, start_time, end_time, puuid);")
    
    def get_query_start_index(
        self,
        platform: str,
        start_time: str,
        end_time: str,
        player_id: str,
    ) -> int:
        """
        Get the start index for match querying.
        
        Args:
            platform: Platform identifier (e.g., "NA1")
            start_time: Start time string
            end_time: End time string
            player_id: Player UUID (puuid)
            
        Returns:
            Start index (0 if not found)
        """
        result = self.con.execute(
            """
            SELECT last_start_index 
            FROM query_progress
            WHERE platform = ? AND start_time = ? AND end_time = ? AND puuid = ?
            """,
            [platform, start_time, end_time, player_id]
        ).fetchone()
        
        return result[0] if result else 0
    
    def update_start_index(
        self,
        platform: str,
        start_time: str,
        end_time: str,
        puuid: str,
        last_start_index: int,
    ) -> None:
        """
        Update the last queried start index for a specific query context.
        
        Args:
            platform: Platform identifier (e.g., "NA1")
            start_time: Start time string
            end_time: End time string
            puuid: Player UUID
            last_start_index: The last start index that was queried
        """
        self.con.execute(
            """
            INSERT INTO query_progress (platform, start_time, end_time, puuid, last_start_index, last_updated)
            VALUES (?, ?, ?, ?, ?, NOW())
            ON CONFLICT (platform, start_time, end_time, puuid) 
            DO UPDATE SET 
                last_start_index = excluded.last_start_index,
                last_updated = NOW()
            """,
            [platform, start_time, end_time, puuid, last_start_index]
        )
    
    def clear_all_data(self) -> None:
        """
        Remove all data from the database.
        
        This will delete all rows from the query_progress table.
        The table and indexes will remain intact.
        """
        self.con.execute("DELETE FROM query_progress")
    
    def close(self):
        """Close the database connection."""
        self.con.close()
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting context."""
        self.close()


def _main():
    """Example usage: clear all data from both databases."""
    # Clear matches database
    with MatchDatabase("data/match_data/matches.duckdb") as db:
        print("Clearing all data from matches database...")
        db.clear_all_data()
        print("Matches database cleared successfully!")
    
    # Clear query progress database
    with QueryProgressTracker("data/match_data/query_progress.duckdb") as tracker:
        print("Clearing all data from query progress database...")
        tracker.clear_all_data()
        print("Query progress database cleared successfully!")


if __name__ == "__main__":
    _main()