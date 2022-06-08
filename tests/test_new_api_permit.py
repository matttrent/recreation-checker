import datetime as dt
import pytest
from typing import Any

from recreation.newapi.api_permit import (
    RGApiPermit,
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
