import datetime as dt

import apiclient.exceptions
import backoff

from apiclient import (    
    APIClient,
    endpoint,
    JsonResponseHandler,
    JsonRequestFormatter,
)
from apiclient_pydantic import serialize_all_methods
from fake_useragent import UserAgent

from ..core import IntOrStr
from .camp import (
    RGApiCampground,
    RGApiCampsite,
    RGApiCampgroundAvailability,
)
from .extra import LocationType, RGApiAlert, RGApiRatingAggregate
from .permit import (
    RGApiPermit,
    RGApiPermitAvailability,
    RGApiPermitInyoAvailability,
)


BACKOFF_EXCEPTIONS = (
    apiclient.exceptions.APIClientError,
)
BACKOFF_TRIES = 5


@endpoint(base_url="https://www.recreation.gov/api")
class RecreationGovEndpoint:
    campground = "camps/campgrounds/{id}"
    campground_sites = "camps/campgrounds/{id}/campsites"
    campsite = "camps/campsites/{id}"
    permit = "permitcontent/{id}"

    alert = "communication/external/alert"
    rating_aggregate = "ratingreview/aggregate"

    campground_availability = "camps/availability/campground/{id}/month"
    permit_availability = "permits/{id}/availability/month" 
    permitinyo_availability = "permitinyo/{id}/availability"


@serialize_all_methods()
class RecreationGovClient(APIClient):

    def __init__(self):
        super().__init__(
            response_handler=JsonResponseHandler,
            request_formatter=JsonRequestFormatter,
        )

    def get_default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = super().get_default_headers()
        headers["User-Agent"] = UserAgent().random
        return headers

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_campground(self, campground_id: IntOrStr) -> RGApiCampground:
        url = RecreationGovEndpoint.campground.format(id=campground_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        return resp["campground"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_campground_sites(self, campground_id: IntOrStr) -> list[RGApiCampsite]:
        url = RecreationGovEndpoint.campground_sites.format(id=campground_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        return resp["campsites"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_campsite(self, campsite_id: IntOrStr) -> RGApiCampsite:
        url = RecreationGovEndpoint.campsite.format(id=campsite_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        return resp["campsite"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_permit(self, permit_id: IntOrStr) -> RGApiPermit:
        url = RecreationGovEndpoint.permit.format(id=permit_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        return resp["payload"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_alerts(
        self, location_id: IntOrStr, location_type: LocationType
    ) -> list[RGApiAlert]:
        url = RecreationGovEndpoint.alert.format()
        headers = self.get_default_headers()
        params = {
            "location_id": location_id,
            "location_type": location_type.value
        }
        resp = self.get(url, headers=headers, params=params)
        return resp["alerts"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_ratings(
        self, location_id: IntOrStr, location_type: LocationType
    ) -> RGApiRatingAggregate:
        url = RecreationGovEndpoint.rating_aggregate.format()
        headers = self.get_default_headers()
        params = {
            "location_id": location_id,
            "location_type": location_type.value
        }
        resp = self.get(url, headers=headers, params=params)
        return resp

    @staticmethod
    def _format_date(date_object: dt.datetime, with_ms: bool = True) -> str:
        ms = ".000" if with_ms else ""
        date_formatted = dt.datetime.strftime(date_object, f"%Y-%m-%dT00:00:00{ms}Z")
        return date_formatted

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_campground_availability(
        self, campground_id: IntOrStr, start_date: dt.date
    ) -> RGApiCampgroundAvailability:
        url = RecreationGovEndpoint.campground_availability.format(id=campground_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        resp = self.get(url, headers=headers, params=params)
        return resp

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_permit_availability(
        self, permit_id: IntOrStr, start_date: dt.date
    ) -> RGApiPermitAvailability:
        url = RecreationGovEndpoint.permit_availability.format(id=permit_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        resp = self.get(url, headers=headers, params=params)
        return resp["payload"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_permit_inyo_availability(
        self, permit_id: IntOrStr, start_date: dt.date
    ) -> RGApiPermitInyoAvailability:
        url = RecreationGovEndpoint.permitinyo_availability.format(id=permit_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        return self.get(url, headers=headers, params=params) 
