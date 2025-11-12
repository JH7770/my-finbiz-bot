import json
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from technical_analyzer import (
    analyze_top10_technical,
    load_technical_snapshot,
    detect_ma60_breaks,
    detect_trailing_stops,
)


TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE"]


SNAPSHOT_DATA = {
    "2024-12-27": {
        "AAA": {
            "status": "success",
            "price": 101.0,
            "ma20": 105.0,
            "ma60": 95.0,
            "ma120": 90.0,
            "above_ma20": False,
            "above_ma60": True,
            "above_ma120": True,
            "ma60_above_ma120": True,
            "all_conditions_met": False,
        },
        "BBB": {
            "status": "success",
            "price": 200.0,
            "ma20": 198.0,
            "ma60": 190.0,
            "ma120": 185.0,
            "above_ma20": True,
            "above_ma60": True,
            "above_ma120": True,
            "ma60_above_ma120": True,
            "all_conditions_met": True,
        },
        "CCC": {"status": "error"},
        "DDD": {"status": "error"},
        "EEE": {"status": "error"},
    },
    "2024-12-30": {
        "AAA": {
            "status": "success",
            "price": 90.0,
            "ma20": 104.0,
            "ma60": 95.0,
            "ma120": 92.0,
            "above_ma20": False,
            "above_ma60": False,
            "above_ma120": False,
            "ma60_above_ma120": True,
            "all_conditions_met": False,
        },
        "BBB": {
            "status": "success",
            "price": 201.0,
            "ma20": 198.5,
            "ma60": 190.5,
            "ma120": 186.0,
            "above_ma20": True,
            "above_ma60": True,
            "above_ma120": True,
            "ma60_above_ma120": True,
            "all_conditions_met": True,
        },
        "CCC": {"status": "error"},
        "DDD": {"status": "error"},
        "EEE": {"status": "error"},
    },
    "2024-12-31": {
        "AAA": {
            "status": "success",
            "price": 88.0,
            "ma20": 103.0,
            "ma60": 94.0,
            "ma120": 91.0,
            "above_ma20": False,
            "above_ma60": False,
            "above_ma120": False,
            "ma60_above_ma120": True,
            "all_conditions_met": False,
        },
        "BBB": {
            "status": "success",
            "price": 202.0,
            "ma20": 199.0,
            "ma60": 191.0,
            "ma120": 186.5,
            "above_ma20": True,
            "above_ma60": True,
            "above_ma120": True,
            "ma60_above_ma120": True,
            "all_conditions_met": True,
        },
        "CCC": {"status": "error"},
        "DDD": {"status": "error"},
        "EEE": {"status": "error"},
    },
}


def _make_dataframe():
    return pd.DataFrame({"Ticker": TICKERS})


def _make_status_factory(day):
    def _factory(ticker):
        data = SNAPSHOT_DATA[day][ticker]
        return json.loads(json.dumps(data))

    return _factory


def test_snapshot_roundtrip_across_weekend(tmp_path):
    df = _make_dataframe()
    technical_dir = tmp_path / "technical"
    technical_dir.mkdir()

    for day in ["2024-12-27", "2024-12-30", "2024-12-31"]:
        with patch("technical_analyzer.calculate_ma_status", side_effect=_make_status_factory(day)):
            analysis, snapshot = analyze_top10_technical(
                df,
                as_of_date=day,
                screener_type="large",
                output_dir=str(technical_dir),
                return_snapshot=True,
            )

        saved_path = technical_dir / f"large_{day}.json"
        assert saved_path.exists()

        loaded_snapshot = load_technical_snapshot("large", day, base_dir=str(technical_dir))
        assert loaded_snapshot is not None
        assert loaded_snapshot["version"] == 1
        assert loaded_snapshot["as_of"] == day
        assert loaded_snapshot["results"]["AAA"]["price"] == SNAPSHOT_DATA[day]["AAA"]["price"]
        assert analysis["AAA"]["price"] == SNAPSHOT_DATA[day]["AAA"]["price"]

    friday_snapshot = load_technical_snapshot("large", "2024-12-27", base_dir=str(technical_dir))
    monday_snapshot = load_technical_snapshot("large", "2024-12-30", base_dir=str(technical_dir))
    tuesday_snapshot = load_technical_snapshot("large", "2024-12-31", base_dir=str(technical_dir))

    with patch("technical_analyzer.calculate_atr", return_value={"atr": 2.0, "atr_pct": 4.0}), \
         patch(
             "technical_analyzer.calculate_ma20_slope",
             return_value={"ma20_today": 0, "ma20_yesterday": 0, "slope": -0.5, "is_declining": True},
         ):
        ma60_breaks = detect_ma60_breaks(monday_snapshot, friday_snapshot)
        assert [entry["ticker"] for entry in ma60_breaks] == ["AAA"]

        trailing_stops = detect_trailing_stops(monday_snapshot, friday_snapshot)
        assert [entry["ticker"] for entry in trailing_stops] == ["AAA"]

        trailing_stops_next = detect_trailing_stops(tuesday_snapshot, monday_snapshot)
        assert [entry["ticker"] for entry in trailing_stops_next] == ["AAA"]
