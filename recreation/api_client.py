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

from .api_camp import (
    RGApiCampground,
    RGApiCampsite,
    RGApiCampgroundAvailability,
)
from .core import IntOrStr
from .api_permit import (
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
    alert = "communication/external/alert"

    campground = "camps/campgrounds/{id}"
    campsite = "camps/campsites/{id}"
    permit = "permitcontent/{id}"

    campground_availability = "camps/availability/campground/{id}/month"
    permit_availability = "permits/{id}/availability/month" 
    permitinyo_availability = "permitinyo/{id}/availability"


# class JsonPayloadResponseHandler(JsonResponseHandler):
    
#     @staticmethod
#     def get_request_data(response: Response) -> Optional[JsonType]:
#         response_json = JsonResponseHandler.get_request_data(response)
#         return response_json["payload"]


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
        # print("facility_type", resp["campground"]["facility_type"])
        return resp["campground"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_campsite(self, campsite_id: IntOrStr) -> RGApiCampsite:
        url = RecreationGovEndpoint.campsite.format(id=campsite_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        # print("campsite_status", resp["campsite"]["campsite_status"])
        # print("campsite_type", resp["campsite"]["campsite_type"])
        return resp["campsite"]

    @backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS, max_tries=BACKOFF_TRIES)
    def get_permit(self, permit_id: IntOrStr) -> RGApiPermit:
        url = RecreationGovEndpoint.permit.format(id=permit_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)

        # division_types = set(
        #     divis["type"]
        #     for divis in resp["payload"]["divisions"].values()
        # )
        # print("division types", division_types)

        return resp["payload"]

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

        # campsite_reserve_types = set(
        #     campsite["campsite_reserve_type"]
        #     for campsite in resp["campsites"].values()
        # )
        # print("campsite reserve types", campsite_reserve_types)

        # campsite_types = set(
        #     campsite["campsite_type"]
        #     for campsite in resp["campsites"].values()
        # )
        # print("campsite types", campsite_types)

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
