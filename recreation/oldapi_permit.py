import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, cast

from dateutil import rrule

from recreation.oldapi_core import (
    BASE_URL,
    ApiResponse,
    ItemId,
    format_date,
    generate_params,
    send_request,
)

PERMIT_ENDPOINT = "/api/permits/"
AVAILABILITY_ENDPOINT = "/api/permits/availability/"


class Division:
    id: ItemId
    name: str
    div_type: str
    response: ApiResponse

    def __init__(self, response: ApiResponse) -> None:
        self.id = response["id"]
        self.name = response["name"]
        self.div_type = response["type"]
        self.response = response

    def __repr__(self) -> str:
        return f"<Division:{self.id} {self.name}>"


class Entrance:
    id: ItemId
    name: str
    response: ApiResponse


class PermitAvailability:
    avails: Dict[ItemId, List]


class Permit:
    id: ItemId
    name: str
    divisions: Dict[ItemId, Division]
    response: ApiResponse

    def __init__(self, response: ApiResponse) -> None:
        self.id = response["id"]
        self.name = response["name"]
        self.divisions = {
            id: Division(div) for id, div in response["divisions"].items()
        }
        self.response = response

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/permits/{self.id}"

    def __repr__(self) -> str:
        return f"<Permit:{self.id} {self.name}>"

    @staticmethod
    def fetch_permit(permit_id: ItemId) -> "Permit":
        url = f"{BASE_URL}{PERMIT_ENDPOINT}{permit_id}/details"
        resp = send_request(url, None)
        permit = Permit(resp["payload"])
        return permit
