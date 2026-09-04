"""Runtime smoke test for the NGDP Web V1 application."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_renders_without_runtime_errors():
    dashboard_path = Path(__file__).resolve().parent.parent / "src" / "dashboard.py"

    app = AppTest.from_file(dashboard_path, default_timeout=15).run()

    assert not app.exception
    assert len(app.metric) == 4
    assert app.metric[0].label == "Latest monthly output"
    assert app.metric[1].label == "Renewable share"
