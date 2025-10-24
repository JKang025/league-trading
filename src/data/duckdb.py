import duckdb
from typing import Iterable
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
            rows.append([
                m.match_id,
                p.puuid,
                p.champion,
                p.individual_position,
                p.team_position,
                p.team_id,
                p.win,
                getattr(p, "rank_num", None)  # if you add it later
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
    """Example usage of the new MatchDatabase class."""
    with MatchDatabase("data/match_data/matches.duckdb") as db:
        print("Database initialized successfully!")


if __name__ == "__main__":
    _main()