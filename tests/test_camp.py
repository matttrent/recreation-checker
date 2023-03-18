import datetime as dt
import pytest
from typing import Any, Dict

from recreation.rgapi.camp import (
    CampsiteAvailabilityStatus,
    RGApiCampground,
    RGApiCampgroundAvailability,
    RGApiCampsite,
    CampgroundType,
    CampsiteReserveType,
    CampsiteStatus,
    CampsiteType,
    RgApiCampsiteAvailability,
)


@pytest.fixture
def campsite_data() -> dict[str, Any]:
    return {
        'campsite_id': '64082',
        'campsite_latitude': 41.578691,
        'campsite_longitude': -121.658252,
        'campsite_name': '001',
        'campsite_reserve_type': 'Site-Specific',
        'campsite_status': 'Open',
        'campsite_type': 'CABIN NONELECTRIC',
        'facility_id': '234436',
        'loop': 'AREA LITTLE MT. HOFFMAN LOOKOUT',
        'parent_site_id': None
    }


@pytest.fixture
def campsite(campsite_data) -> RGApiCampsite:
    return RGApiCampsite(**campsite_data)


@pytest.fixture
def campground_data() -> dict[str, Any]:
    return {
        'campsites': ['64082'],
        'facility_email': '',
        'facility_id': '234436',
        'facility_latitude': 41.5786111,
        'facility_longitude': -121.6597222,
        'facility_map_url': '',
        'facility_name': 'LITTLE MT. HOFFMAN LOOKOUT',
        'facility_phone': '530-964-2184',
        'facility_type': 'STANDARD',
        'parent_asset_id': '1073'
    }


@pytest.fixture
def campground(campground_data) -> RGApiCampground:
    return RGApiCampground(**campground_data)


def test_campsite_init(campsite_data):
    campsite = RGApiCampsite(**campsite_data)
    assert campsite.id == "64082"
    assert campsite.latitude == 41.578691
    assert campsite.longitude == -121.658252
    assert campsite.name == "001"
    assert campsite.reserve_type == CampsiteReserveType.site_specific
    assert campsite.status == CampsiteStatus.open
    assert campsite.campsite_type == CampsiteType.cabin_nonelectric
    assert campsite.campground_id == "234436"


def test_campground_init(campground_data):
    campground = RGApiCampground(**campground_data)
    assert campground.campsite_ids == ['64082']
    assert campground.email == ''
    assert campground.id == '234436'
    assert campground.latitude == 41.5786111
    assert campground.longitude == -121.6597222
    assert campground.map_url == ''
    assert campground.name == 'LITTLE MT. HOFFMAN LOOKOUT'
    assert campground.phone == '530-964-2184'
    assert campground.campground_type == CampgroundType.standard


@pytest.fixture
def campground_availability_data() -> dict[str, Any]:
    return {
        "campsites": {
            "64082": {
                "availabilities": {
                    "2022-07-01T00:00:00Z": "Available",
                    "2022-07-02T00:00:00Z": "Available",
                    "2022-07-03T00:00:00Z": "Not Available",
                },
                "campsite_id": "64082",
                "campsite_reserve_type": "Site-Specific",
                "campsite_type": "CABIN NONELECTRIC",
                "loop": "AREA LITTLE MT. HOFFMAN LOOKOUT",
                "max_num_people": 4,
                "min_num_people": 1,
                "site": "001",
                "type_of_use": "Overnight",
            }
        }
    }


@pytest.fixture
def campground_availability(campground_availability_data):
    return RGApiCampgroundAvailability(**campground_availability_data)


def test_campground_availability_init(campground_availability_data):
    camp_avail = RGApiCampgroundAvailability(**campground_availability_data)
    site = camp_avail.campsites["64082"]
    assert site.id == "64082"
    assert site.reserve_type == CampsiteReserveType.site_specific

    assert (
        site.availabilities[dt.datetime(2022, 7, 1, tzinfo=dt.timezone.utc)] ==
        CampsiteAvailabilityStatus.available
    )
    assert (
        site.availabilities[dt.datetime(2022, 7, 2, tzinfo=dt.timezone.utc)] ==
        CampsiteAvailabilityStatus.available
    )
    assert (
        site.availabilities[dt.datetime(2022, 7, 3, tzinfo=dt.timezone.utc)] ==
        CampsiteAvailabilityStatus.not_available
    )
