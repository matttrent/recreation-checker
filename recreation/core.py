import datetime as dt
import threading
from typing import Any, Dict, Optional

import requests
from fake_useragent import UserAgent

ItemId = int
ApiResponse = Dict[str, Any]

BASE_URL = "https://www.recreation.gov"

HEADERS: Dict[str, str] = {"User-Agent": UserAgent().random}

THREAD_LOCAL = threading.local()


def get_session():
    if not hasattr(THREAD_LOCAL, "session"):
        THREAD_LOCAL.session = requests.Session()
    return THREAD_LOCAL.session


def format_date(date_object: dt.datetime, with_ms: bool = True) -> str:
    ms = ".000" if with_ms else ""
    date_formatted = dt.datetime.strftime(date_object, f"%Y-%m-%dT00:00:00{ms}Z")
    return date_formatted


def generate_params(start_date: dt.datetime) -> Dict[str, str]:
    start_date = start_date.replace(day=1)
    params = {
        "start_date": format_date(start_date),
    }
    return params


def send_request(url: str, params: Optional[Dict[str, str]]) -> ApiResponse:
    session = get_session()
    resp = session.get(url, params=params, headers=HEADERS)
    if resp.status_code != 200:
        raise RuntimeError(
            "failedRequest",
            "ERROR, {} code received from {}: {}".format(
                resp.status_code, url, resp.text
            ),
        )
    return resp.json()
