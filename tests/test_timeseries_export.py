from __future__ import annotations

from pathlib import Path

from src.simulation.export_timeseries import rows_to_csv


def test_rows_to_csv_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "out.csv"

    rows = [
        {
            "time": "2022-01-01T00:00:00+00:00",
            "market": "DE-LU",
            "stage": "SYSTEM",
            "variable": "day_ahead_price",
            "value": 41.33,
            "unit": "EUR/MWh",
            "source_type": "EXTERNAL",
            "source": "SMARD",
        },
        {
            "time": "2022-01-01T00:00:00+00:00",
            "market": "DE-LU",
            "stage": "CONTROL",
            "variable": "electrolyzer_on",
            "value": 1,
            "unit": "-",
            "source_type": "ASSUMPTION",
            "source": "rule: price < 50 EUR/MWh",
        },
    ]

    written = rows_to_csv(rows=rows, path=out)

    assert written.exists()
    content = written.read_text(encoding="utf-8").strip().splitlines()

    # header + 2 data rows
    assert len(content) == 1 + 2

    # header must contain key columns
    header = content[0]
    assert "time" in header
    assert "market" in header
    assert "variable" in header
    assert "value" in header
