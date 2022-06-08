import datetime as dt
import pytest
from typing import Any

from recreation.newapi.api_camp import (
    RGApiCampground,
    RGApiCampsite,
    CampgroundType,
    CampsiteReserveType,
    CampsiteStatus,
    CampsiteType,
)


@pytest.fixture
def campsite_data():
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
def campground_data():
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

