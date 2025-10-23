import duckdb
from typing import Iterable
from src.data.riot_api import Match

def init_db(db_path: str):
    con = duckdb.connect(db_path)
    con.execute("""CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        game_creation BIGINT,
        game_duration BIGINT,
        game_end_timestamp BIGINT,
        game_mode TEXT,
        game_start_timestamp BIGINT,
        game_type TEXT,
        game_version TEXT
    );""")
    con.execute("""CREATE TABLE IF NOT EXISTS participants (
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
    con.execute("CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants(puuid);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_participants_champion ON participants(champion);")
    return con

def upsert_match(con: duckdb.DuckDBPyConnection, m: Match):
    # Insert the match; ignore if it already exists
    con.execute("""
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
    con.executemany("""
        INSERT INTO participants (
          match_id, puuid, champion, individual_position, team_position,
          team_id, win, rank_num
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_id, puuid) DO NOTHING
    """, rows)

def upsert_many(con: duckdb.DuckDBPyConnection, matches: Iterable[Match]):
    with con:  # single transaction
        for m in matches:
            upsert_match(con, m)

def _main():
    init_db("data/match_data/matches.duckdb")

if __name__ == "__main__":
    _main()