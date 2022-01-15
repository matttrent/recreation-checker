import datetime as dt

from recreation import core


def test_format_date() -> None:
    inp = dt.datetime(2021, 4, 28, 19, 35, 31, 123)
    out = "2021-04-28T00:00:00"
    ms = ".000"
    assert core.format_date(inp, True) == f"{out}{ms}Z"
    assert core.format_date(inp, False) == f"{out}Z"


def test_generate_params() -> None:
    inp = dt.datetime(2021, 4, 28, 19, 35, 31, 123)
    out = {"start_date": "2021-04-01T00:00:00.000Z"}
    assert core.generate_params(inp) == out
