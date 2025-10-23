"""Simple latency tester for RiotAPI wrapper methods.

Run examples:
  python -m src.data.riot_api_latency_testing --platform NA1 --region americas --iterations 3
  python -m src.data.riot_api_latency_testing --puuid <PUUID> --region americas --iterations 5
  python -m src.data.riot_api_latency_testing --match-id <MATCH_ID> --region americas

RIOT_API_KEY must be set in your environment (.env supported by the wrapper).
"""

from __future__ import annotations

from types import SimpleNamespace
import statistics
import time
from typing import Callable, Any

from src.data.riot_api import RiotAPI


def measure_latency(fn: Callable[[], Any], *, iterations: int, label: str) -> None:
    """Measure and print latency stats for a zero-arg callable.

    Each iteration runs independently; exceptions are caught and reported.
    """
    durations: list[float] = []
    errors: list[str] = []

    print(f"\n=== {label} (iterations={iterations}) ===")
    for i in range(1, iterations + 1):
        start = time.perf_counter()
        try:
            _ = fn()
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - start
            errors.append(f"iter {i}: {exc!r}")
            print(f"  iter {i}: ERROR after {elapsed*1000:.1f} ms -> {exc!r}")
        else:
            elapsed = time.perf_counter() - start
            durations.append(elapsed)
            print(f"  iter {i}: {elapsed*1000:.1f} ms")

    if durations:
        avg_ms = statistics.mean(durations) * 1000
        p50_ms = statistics.median(durations) * 1000
        min_ms = min(durations) * 1000
        max_ms = max(durations) * 1000
        # crude p95
        sorted_durs = sorted(durations)
        idx95 = max(0, int(round(0.95 * (len(sorted_durs) - 1))))
        p95_ms = sorted_durs[idx95] * 1000

        print(
            "  -> stats: "
            f"avg={avg_ms:.1f} ms, p50={p50_ms:.1f} ms, p95={p95_ms:.1f} ms, "
            f"min={min_ms:.1f} ms, max={max_ms:.1f} ms"
        )
    if errors:
        print(f"  -> {len(errors)} error(s)")


def main() -> None:
    # argparse temporarily disabled; fill values below instead
    # parser = argparse.ArgumentParser(description="Latency tests for RiotAPI wrapper")
    # parser.add_argument("--platform", default="NA1", help="Platform routing value (e.g., NA1, KR)")
    # parser.add_argument("--region", default="americas", help="Region routing for matches (e.g., americas, asia, europe, sea)")
    # parser.add_argument("--iterations", type=int, default=3, help="Iterations per test")
    #
    # # Optional IDs
    # parser.add_argument("--puuid", default=None, help="PUUID for get_match_ids_by_puuid")
    # parser.add_argument("--match-id", dest="match_id", default=None, help="Match ID for get_match")
    #
    # # Optional tuning for match ids query
    # parser.add_argument("--count", type=int, default=5, help="Count for get_match_ids_by_puuid")
    # parser.add_argument("--start-time", type=int, default=None, help="Epoch seconds startTime filter")
    # parser.add_argument("--end-time", type=int, default=None, help="Epoch seconds endTime filter")
    #
    # args = parser.parse_args()
    args = SimpleNamespace(
        platform="NA1",
        region="americas",
        iterations=3,
        puuid="CcfFcULr3L2rU_JVD6AkuYv_KkTCgYJD9mDKdZZeI0lzig3-bLLet_JV_-SXHdk3L1pAYNJKjyM1oA",        # e.g., "<PUUID>"
        match_id="NA1_5398512753",     # e.g., "<MATCH_ID>"
        count=5,
        start_time=None,
        end_time=None,
    )

    api = RiotAPI()

    # League endpoints (do not require PUUID/Match ID)
    measure_latency(
        lambda: api.get_challenger_league(platform=args.platform),
        iterations=args.iterations,
        label=f"get_challenger_league(platform={args.platform})",
    )
    measure_latency(
        lambda: api.get_grandmaster_league(platform=args.platform),
        iterations=args.iterations,
        label=f"get_grandmaster_league(platform={args.platform})",
    )
    measure_latency(
        lambda: api.get_master_league(platform=args.platform),
        iterations=args.iterations,
        label=f"get_master_league(platform={args.platform})",
    )

    # Match IDs by PUUID (optional)
    if args.puuid:
        measure_latency(
            lambda: api.get_match_ids_by_puuid(
                args.puuid,
                region=args.region,
                start_time=args.start_time,
                end_time=args.end_time,
                start=0,
                count=args.count,
            ),
            iterations=args.iterations,
            label=(
                f"get_match_ids_by_puuid(puuid=<hidden>, region={args.region}, "
                f"count={args.count}, start_time={args.start_time}, end_time={args.end_time})"
            ),
        )
    else:
        print("\n(skipped) get_match_ids_by_puuid: provide --puuid to enable")

    # Match by ID (optional)
    if args.match_id:
        measure_latency(
            lambda: api.get_match(args.match_id, region=args.region),
            iterations=args.iterations,
            label=f"get_match(match_id=<hidden>, region={args.region})",
        )
    else:
        print("\n(skipped) get_match: provide --match-id to enable")


if __name__ == "__main__":
    main()




"""
=== get_challenger_league(platform=NA1) (iterations=3) ===
https://na1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5
  iter 1: 378.9 ms
https://na1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5
  iter 2: 193.8 ms
https://na1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5
  iter 3: 203.3 ms
  -> stats: avg=258.6 ms, p50=203.3 ms, p95=378.9 ms, min=193.8 ms, max=378.9 ms

=== get_grandmaster_league(platform=NA1) (iterations=3) ===
https://na1.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5
  iter 1: 439.1 ms
https://na1.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5
  iter 2: 342.5 ms
https://na1.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5
  iter 3: 343.9 ms
  -> stats: avg=375.2 ms, p50=343.9 ms, p95=439.1 ms, min=342.5 ms, max=439.1 ms

=== get_master_league(platform=NA1) (iterations=3) ===
https://na1.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5
  iter 1: 2236.9 ms
https://na1.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5
  iter 2: 2018.3 ms
https://na1.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5
  iter 3: 1947.2 ms
  -> stats: avg=2067.5 ms, p50=2018.3 ms, p95=2236.9 ms, min=1947.2 ms, max=2236.9 ms

=== get_match_ids_by_puuid(puuid=<hidden>, region=americas, count=5, start_time=None, end_time=None) (iterations=3) ===
https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/CcfFcULr3L2rU_JVD6AkuYv_KkTCgYJD9mDKdZZeI0lzig3-bLLet_JV_-SXHdk3L1pAYNJKjyM1oA/ids
  iter 1: 217.7 ms
https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/CcfFcULr3L2rU_JVD6AkuYv_KkTCgYJD9mDKdZZeI0lzig3-bLLet_JV_-SXHdk3L1pAYNJKjyM1oA/ids
  iter 2: 104.4 ms
https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/CcfFcULr3L2rU_JVD6AkuYv_KkTCgYJD9mDKdZZeI0lzig3-bLLet_JV_-SXHdk3L1pAYNJKjyM1oA/ids
  iter 3: 77.3 ms
  -> stats: avg=133.1 ms, p50=104.4 ms, p95=217.7 ms, min=77.3 ms, max=217.7 ms

=== get_match(match_id=<hidden>, region=americas) (iterations=3) ===
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
  iter 1: 239.8 ms
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
  iter 2: 129.7 ms
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
https://americas.api.riotgames.com/lol/match/v5/matches/NA1_5398512753
  iter 3: 144.3 ms
  -> stats: avg=171.3 ms, p50=144.3 ms, p95=239.8 ms, min=129.7 ms, max=239.8 ms
(venv) jkang@Jeffreys-MacBook-Pro-2 league-trading % 
"""