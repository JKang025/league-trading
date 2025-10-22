import requests

from data.riot_api import Match, RiotAPI


MATCH_ID = "NA1_5395834007"

MATCH_RESPONSE = {
    "metadata": {
        "matchId": MATCH_ID,
    },
    "info": {
        "gameCreation": 1760831116385,
        "gameDuration": 1658,
        "gameEndTimestamp": 1760832858276,
        "gameMode": "CLASSIC",
        "gameStartTimestamp": 1760831199921,
        "gameType": "MATCHED_GAME",
        "gameVersion": "15.20.719.545",
        "participants": [
            {
                "puuid": "PKDb1Hr2KqfmEKLuPeq6rA_uq9K3oKpjo6UX6aH2hd332uVN4phfnomMXTwPRUMRulm_XQ04Xj-f6g",
                "championName": "Camille",
                "individualPosition": "TOP",
                "teamPosition": "TOP",
                "teamId": 100,
                "win": False,
            },
        ],
    },
}


def test_get_match_parses_into_match():
    api = RiotAPI()
    raw_match = api.get_match(MATCH_ID, region="americas")
    match = Match.from_json(raw_match)

    assert match.match_id == MATCH_ID
    assert match.game_creation == MATCH_RESPONSE["info"]["gameCreation"]
    assert match.game_duration == MATCH_RESPONSE["info"]["gameDuration"]
    assert match.game_end_timestamp == MATCH_RESPONSE["info"]["gameEndTimestamp"]
    assert match.game_mode == MATCH_RESPONSE["info"]["gameMode"]
    assert match.game_start_timestamp == MATCH_RESPONSE["info"]["gameStartTimestamp"]
    assert match.game_type == MATCH_RESPONSE["info"]["gameType"]
    assert match.game_version == MATCH_RESPONSE["info"]["gameVersion"]

    assert len(match.participants) == 10

    first_participant = match.participants[0]
    expected_first = MATCH_RESPONSE["info"]["participants"][0]
    assert first_participant.puuid == expected_first["puuid"] #flakey, based on your current api key
    assert first_participant.champion == expected_first["championName"]
    assert first_participant.individual_position == expected_first["individualPosition"]
    assert first_participant.team_position == expected_first["teamPosition"]
    assert first_participant.team_id == expected_first["teamId"]
    assert first_participant.win == expected_first["win"]
