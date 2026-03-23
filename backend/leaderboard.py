import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path(__file__).parent / "leaderboard.json"


def _load() -> list:
    if not LEADERBOARD_PATH.exists():
        return []
    try:
        with open(LEADERBOARD_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list) -> None:
    with open(LEADERBOARD_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def _score(entry: dict) -> float:
    fees = entry.get("total_fees", 0)
    net = entry.get("net_profit", 0)
    return net / fees if fees > 0 else net


def _rank(entries: list) -> list:
    sorted_entries = sorted(entries, key=lambda e: (_score(e), -e.get("initial_capital", 0)), reverse=True)
    for i, entry in enumerate(sorted_entries):
        entry["rank"] = i + 1
        entry["score"] = round(_score(entry), 4)
    return sorted_entries


def generate_name(granularity, bb_period, bb_std, rsi_period,
                  longs_enabled, shorts_enabled, initial_capital, leverage,
                  sl_multiplier, trading_start_time, trading_end_time) -> str:
    if longs_enabled and shorts_enabled:
        direction = "L+S"
    elif longs_enabled:
        direction = "Long"
    else:
        direction = "Short"

    cap = int(initial_capital)
    cap_str = f"${cap // 1000}k" if cap % 1000 == 0 else f"${cap}"
    lev_str = f"×{int(leverage)}" if leverage == int(leverage) else f"×{leverage}"
    sl_str = f"SL:{sl_multiplier}" if sl_multiplier != 1.0 else ""
    hours_str = f"{trading_start_time}-{trading_end_time}"

    parts = [
        granularity,
        f"BB:{bb_period}/{bb_std}",
        f"RSI:{rsi_period}",
        direction,
        f"{cap_str}{lev_str}",
        hours_str,
    ]
    if sl_str:
        parts.append(sl_str)
    return " | ".join(parts)


def add_entry(params: dict, result: dict) -> None:
    net_profit = round(result["total_profit"] - result["total_fees"], 2)
    entry = {
        "id": str(uuid.uuid4()),
        "name": generate_name(
            params["granularity"], params["bb_period"], params["bb_std"],
            params["rsi_period"], params["longs_enabled"], params["shorts_enabled"],
            params["initial_capital"], params["leverage"],
            params["sl_multiplier"], params["trading_start_time"], params["trading_end_time"]
        ),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **params,
        "actual_candles": result["actual_candles"],
        "total_profit": result["total_profit"],
        "total_fees": result["total_fees"],
        "net_profit": net_profit,
        "trade_count": result["trade_count"],
    }
    entries = _load()
    entries.append(entry)
    _save(entries)


def get_entries() -> list:
    return _rank(_load())


def delete_all() -> None:
    _save([])


def delete_one(entry_id: str) -> bool:
    entries = _load()
    new_entries = [e for e in entries if e["id"] != entry_id]
    if len(new_entries) == len(entries):
        return False
    _save(new_entries)
    return True
