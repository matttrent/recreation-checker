import datetime as dt
import pytest

from recreation.newapi.api_camp import CampsiteAvailabilityStatus

from recreation.newapi.availability_list import (
    CampgroundAvailability,
    CampgroundAvailabilityList,
    PermitAvailability,
    PermitAvailabilityList
)

from test_new_api_camp import (
    campground_availability, campground_availability_data
)
from test_new_api_permit import (
    permit_availability, permit_availability_data,
    permit_inyo_availability, permit_inyo_availability_data
)


@pytest.fixture
def campground_availability_list(campground_availability):
    return CampgroundAvailabilityList.from_campground([campground_availability])


def test_campground_availability_list_init(campground_availability_list):
    cal = campground_availability_list
    print(cal.availability)
    assert cal.ids == ["64082"]
    assert cal.dates == [
        dt.date(2022, 7, 1),
        dt.date(2022, 7, 3),
    ]
    assert cal.availability[0] == CampgroundAvailability(
        "64082",
        dt.date(2022, 7, 1),
        CampsiteAvailabilityStatus.available,
        2,
    )
    assert cal.availability[1] == CampgroundAvailability(
        "64082",
        dt.date(2022, 7, 3),
        CampsiteAvailabilityStatus.not_available,
        1,
    )


@pytest.fixture
def permit_availability_list(permit_availability):
    return PermitAvailabilityList.from_permit([permit_availability])


@pytest.fixture
def permit_inyo_availability_list(permit_inyo_availability):
    return PermitAvailabilityList.from_permit_inyo([permit_inyo_availability])
