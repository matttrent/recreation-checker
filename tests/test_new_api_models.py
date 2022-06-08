import datetime as dt
import json
import pytest
from typing import Any

from recreation.new_api import (
    RGApiCampsite,
    CampsiteReserveType,
    CampsiteStatus,
    CampsiteType,
)


@pytest.fixture
def campsite_data() -> dict[str, Any]:
    return {
        "campsite_id": "1228", 
        "campsite_latitude": 0.0, 
        "campsite_longitude": 0.0, 
        "campsite_name": "A063", 
        "campsite_reserve_type": "Non Site-Specific", 
        "campsite_status": "Not Available", 
        "campsite_type": "STANDARD NONELECTRIC", 
        "facility_id": "232448", 
        "loop": "A001-A075", 
        "parent_site_id": "409076"
    }


@pytest.fixture
def campground_data():
    return None


def test_campsite_init(campsite_data):
    campsite = RGApiCampsite(**campsite_data)
    assert campsite.id == "1228"
    assert campsite.latitude == 0.0
    assert campsite.longitude == 0.0
    assert campsite.name == "A063"
    assert campsite.reserve_type == CampsiteReserveType.non_site_specific
    assert campsite.status == CampsiteStatus.not_available
    assert campsite.campsite_type == CampsiteType.standard_nonelectric
    assert campsite.campground_id == "232448"
    assert campsite.loop == "A001-A075"
    assert campsite.parent_site_id == "409076"


def test_campground_init(campground_data):
    pass
