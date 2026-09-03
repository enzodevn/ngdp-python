"""Tests for analytical calculations."""

import pandas as pd
import pytest

from src.analytics import calculate_statistics


def test_calculate_statistics() -> None:
    df = pd.DataFrame({"production_mwh": [100, 200, 300]})

    assert calculate_statistics(df) == {
        "total": 600.0,
        "media": 200.0,
        "maximo": 300.0,
        "minimo": 100.0,
    }


def test_calculate_statistics_rejects_empty_data() -> None:
    df = pd.DataFrame({"production_mwh": []})

    with pytest.raises(ValueError, match="dados vazios"):
        calculate_statistics(df)
