import datetime as dt
import pytest
from typing import Any

from recreation.rgapi.permit import (
    RGApiPermit,
    RGApiPermitAvailability,
    RGApiPermitInyoAvailability,
    RgApiPermitDivision,
    RgApiPermitEntrance
)


@pytest.fixture
def permit_division_data():
    return {
        'code': '',
        'district': 'Desolation Wilderness',
        'description': 
            'This zone is in the center of the Rockbound Valley with the Rubicon River ' 
            'paralleling the Rubicon Trail. Camper Flat is a multi-destination hub.',
        'entry_ids': ['106',],
        'exit_ids': ['106'],
        'id': '290',
        'latitude': 0.0,
        'longitude': 0.0,
        'name': '11 Camper Flat',
        'type': 'Destination Zone'
    }


@pytest.fixture
def permit_division(permit_division_data):
    return RgApiPermitDivision(**permit_division_data)


@pytest.fixture
def permit_entrance_data() -> dict[str, Any]:
    return {
        'has_parking': True,
        'id': '106',
        'name': 'Pyramid Creek (Twin Bridges)',
        'is_entry': True,
        'is_exit': True,
        'is_issue_station': False,
        'latitude': 0.0,
        'longitude': 0.0,
        'town': ''
    }


@pytest.fixture
def permit_entrance(permit_entrance_data):
    return RgApiPermitEntrance(**permit_entrance_data)


@pytest.fixture
def permit_data(permit_division_data, permit_entrance_data) -> dict[str, Any]:
    return {
        'id': '233261',
        'name': 'Desolation Wilderness Permit',
        'divisions': {
            '290': permit_division_data,
        },
        'entrances': [
            {
                'has_parking': False,
                'id': '72259',
                'name': 'Eldorado Forest Service Office',
                'is_entry': False,
                'is_exit': False,
                'is_issue_station': True,
                'latitude': 0.0,
                'longitude': 0.0,
                'town': ''
            },
            permit_entrance_data,
        ]
    }


@pytest.fixture
def permit(permit_data):
    return RGApiPermit(**permit_data)


def test_permit_division_init(permit_division_data):
    division = RgApiPermitDivision(**permit_division_data)
    assert division.district == 'Desolation Wilderness'
    assert division.id == '290'
    assert division.division_type == 'Destination Zone'


def test_permit_entrance_init(permit_entrance_data):
    entrance = RgApiPermitEntrance(**permit_entrance_data)
    assert entrance.id == '106'
    assert entrance.name == 'Pyramid Creek (Twin Bridges)'


def test_permit_init(permit_data, permit_division, permit_entrance):
    permit = RGApiPermit(**permit_data)
    assert permit.id == '233261'
    assert permit.name == 'Desolation Wilderness Permit'
    assert len(permit.divisions) == 1
    assert permit.divisions['290'] == permit_division
    assert len(permit.entrance_list) == 2
    assert permit.entrance_list[0].id == '72259'
    assert permit.entrance_list[1] == permit_entrance


@pytest.fixture
def permit_availability_data() -> dict[str, Any]:
    return {
        "permit_id": "233261",
        "next_available_date": "2022-07-01T00:00:00Z",
        "availability": {
            "290": {
                "division_id": "290",
                "date_availability": {
                    "2022-07-01T00:00:00Z": {
                        "total": 14,
                        "remaining": 0,
                        "show_walkup": True,
                        "is_secret_quota": False
                    },
                    "2022-07-02T00:00:00Z": {
                        "total": 14,
                        "remaining": 1,
                        "show_walkup": False,
                        "is_secret_quota": False
                    },
                    "2022-07-03T00:00:00Z": {
                        "total": 14,
                        "remaining": 10,
                        "show_walkup": False,
                        "is_secret_quota": False
                    },
                    "2022-07-04T00:00:00Z": {
                        "total": 14,
                        "remaining": 14,
                        "show_walkup": False,
                        "is_secret_quota": False
                    },
                },
            },
            "291": {
                "division_id": "291",
                "date_availability": {
                    "2022-07-01T00:00:00Z": {
                        "total": 14,
                        "remaining": 0,
                        "show_walkup": True,
                        "is_secret_quota": False
                    },
                    "2022-07-02T00:00:00Z": {
                        "total": 14,
                        "remaining": 0,
                        "show_walkup": True,
                        "is_secret_quota": False
                    },
                    "2022-07-03T00:00:00Z": {
                        "total": 14,
                        "remaining": 0,
                        "show_walkup": True,
                        "is_secret_quota": False
                    },
                    "2022-07-04T00:00:00Z": {
                        "total": 14,
                        "remaining": 0,
                        "show_walkup": True,
                        "is_secret_quota": False
                    },
                },
            },
        }
    }


@pytest.fixture
def permit_availability(permit_availability_data):
    return RGApiPermitAvailability(**permit_availability_data)


def test_permit_availability_init(permit_availability_data):
    permit_avail = RGApiPermitAvailability(**permit_availability_data)

    assert permit_avail.permit_id == "233261"
    assert permit_avail.next_available_date == dt.datetime(
        2022, 7, 1, tzinfo=dt.timezone.utc
    )

    divisions = set(["290", "291"])
    assert divisions == set(permit_avail.availability.keys())

    dates = set(
        dt.datetime(2022, 7, i, tzinfo=dt.timezone.utc)
        for i in range(1, 5)
    )

    for divis in divisions:
        assert (
            dates == 
            set(permit_avail.availability[divis].date_availability.keys())
        )


@pytest.fixture
def permit_inyo_availability_data() -> dict[str, Any]:
    return {
        "payload": {
            "2022-07-01": {
                "424": {
                    "total": 8, "remaining": 5, "is_walkup": False
                },
                "425": {
                    "total": 10, "remaining": 2, "is_walkup": False
                },
                "441": {
                    "total": 900000, "remaining": 900000, "is_walkup": False
                },
            },
            "2022-07-02": {
                "424": {
                    "total": 8, "remaining": 4, "is_walkup": False
                },
                "425": {
                    "total": 10, "remaining": 2, "is_walkup": False
                },
                "441": {
                    "total": 900000, "remaining": 900000, "is_walkup": False
                },
            },
            "2022-07-03": {
                "424": {
                    "total": 8, "remaining": 5, "is_walkup": False
                },
                "425": {
                    "total": 10, "remaining": 6, "is_walkup": False
                    },
                "441": {
                    "total": 900000, "remaining": 900000, "is_walkup": False
                },
            }
        }
    }


@pytest.fixture
def permit_inyo_availability(permit_inyo_availability_data):
    return RGApiPermitInyoAvailability(**permit_inyo_availability_data)


def test_permit_inyo_availability_init(permit_inyo_availability_data):
    permit_avail = RGApiPermitInyoAvailability(**permit_inyo_availability_data)

    dates = set(
        dt.date(2022, 7, i)
        for i in range(1, 4)
    )
    assert dates == permit_avail.payload.keys()

    divisions = set(["424", "425", "441"])
    for date in dates:
        assert permit_avail.payload[date].keys() == divisions
