import datetime as dt
import pytest

from recreation.api_camp import CampsiteAvailabilityStatus

from recreation.availability_list import (
    CampgroundAvailability,
    CampgroundAvailabilityList,
    PermitAvailability,
    PermitAvailabilityList
)

from test_camp import (
    campground_availability, campground_availability_data
)
from test_permit import (
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
    assert len(cal.availability) == 2
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


def test_permit_availability_list(permit_availability_list):
    pal = permit_availability_list
    print(pal.availability)
    assert pal.ids == ["290", "291"]
    assert pal.dates == [
        dt.date(2022, 7, 1),
        dt.date(2022, 7, 2),
        dt.date(2022, 7, 3),
        dt.date(2022, 7, 4),
    ]
    assert len(pal.availability) == 8
    assert pal.availability[0] == PermitAvailability(
        "290",
        dt.date(2022, 7, 1),
        total=14, remaining=0, is_walkup=True
    )
    assert pal.availability[1] == PermitAvailability(
        "290",
        dt.date(2022, 7, 2),
        total=14, remaining=1, is_walkup=False
    )
    assert pal.availability[4] == PermitAvailability(
        "291",
        dt.date(2022, 7, 1),
        total=14, remaining=0, is_walkup=True
    )


def test_permit_inyo_availability_list(permit_inyo_availability_list):
    pal = permit_inyo_availability_list
    print(pal.availability)
    assert pal.ids == ["424", "425", "441"]
    assert pal.dates == [
        dt.date(2022, 7, 1),
        dt.date(2022, 7, 2),
        dt.date(2022, 7, 3),
    ]
    assert len(pal.availability) == 9
    assert pal.availability[0] == PermitAvailability(
        "424",
        dt.date(2022, 7, 1),
        total=8, remaining=5, is_walkup=False
    )
    assert pal.availability[4] == PermitAvailability(
        "425",
        dt.date(2022, 7, 2),
        total=10, remaining=2, is_walkup=False
    )
    assert pal.availability[8] == PermitAvailability(
        "441",
        dt.date(2022, 7, 3),
        total=900000, remaining=900000, is_walkup=False
    )
