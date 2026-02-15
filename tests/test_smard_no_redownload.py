from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.simulation.run_hourly_loop import run_hourly_minimal_exergy


def test_smard_second_run_does_not_download(monkeypatch):
    """
    If SMARD data is already cached, the second run must NOT hit the network.
    """

    def forbidden_post(*args, **kwargs):
        raise AssertionError("Network call attempted despite cache being present")

    # Monkeypatch requests.post used by smard_download_manager
    monkeypatch.setattr("requests.post", forbidden_post)

    start = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2022, 1, 1, 3, 0, tzinfo=timezone.utc)

    # If cache exists, this must run without triggering requests.post
    run_hourly_minimal_exergy(start, end, market="DE-LU")
