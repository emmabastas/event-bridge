from typing import *
from util import memoize, curry
import time
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver


""""
Top-level
"""


def events_for_profile(d: WebDriver, profilename: str):
    prerender, postrender = memoize(
        "fb_page_events_for_profile",
        curry(fetch_page__events_for_profile)(d)
    )(profilename)

    prerenderdata = extract_partial_events(prerender)

    ids = extract_event_ids(postrender)

    events = []
    for id in ids:
        event_page = memoize(
            "fb_page_event",
            curry(fetch_page__event)(d)
        )(id)
        events.append(extract_event_details(event_page))

    generic_events = [parse_event_details(e) for e in events]

    return {
        "prerenderdata": prerenderdata,
        "ids": ids,
        "events": generic_events
    }


"""
Processing profiles-hosted-events pages
"""


EventsForProfileHtml = NewType("EventsForProfileHtml", str)
EventsForProfileHtmlAfterRender = NewType("EventsForProfileHtmlAfterRender", str)
FetchedFbPageEventsForProfile = Tuple[EventsForProfileHtml, EventsForProfileHtmlAfterRender]


def fetch_page__events_for_profile(d: WebDriver, profile: str) -> FetchedFbPageEventsForProfile:
    d.get(f"https://wwww.facebook.com/{profile}/upcoming_hosted_events")

    prerender = d.page_source

    try:
        cockiebutton = WebDriverWait(d, timeout=3).until(
            lambda d: d.find_element(By.CSS_SELECTOR, '[aria-label="Only allow essential cookies"]')
        )
        cockiebutton.click()
    except TimeoutError:
        pass

    d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    laterender = d.execute_script("return document.body.innerHTML;")

    return (
        EventsForProfileHtml(prerender),
        EventsForProfileHtmlAfterRender(laterender)
    )


def extract_partial_events(prerender: EventsForProfileHtml) -> List[Dict[str, Any]]:
    matches = [m for m in re.finditer('"node":{"__typename":"Event"', prerender)]

    object_starts = [m.start()+7 for m in matches]

    dicts = []
    for i in object_starts:
        d = {}
        try:
            d = json.loads(prerender[i:])
        except json.decoder.JSONDecodeError as err:
            if err.msg != "Extra data":
                raise err

            d = json.loads(prerender[i:i+err.pos])

        dicts.append(d)

    return dicts


def extract_event_ids(laterender: EventsForProfileHtmlAfterRender) -> List[str]:
    matches = re.finditer("https:\\/\\/www.facebook.com\\/events\\/(\\d*)\\/", laterender)

    # We care about the order of the id's. Id's appearing sooner means that the events
    # is comming up sooner, it can be nice to have that information preserved.
    ids = [match.group(1) for match in matches]
    no_duplicates = sorted(set(ids), key=lambda x: ids.index(x))

    return no_duplicates


"""
Processing event pages
"""


class FetchedFbPageEvent(TypedDict):
    id: str
    title: str
    source: str
    cover_image_url: str


def fetch_page__event(d: WebDriver, event_id: str) -> FetchedFbPageEvent:
    d.get(f"https://wwww.facebook.com/events/{event_id}/")

    source = d.page_source
    title = d.title

    cover_image_url = None
    try:
        cover_image = WebDriverWait(d, timeout=3).until(
            lambda d: d.find_element(By.CSS_SELECTOR, '[data-imgperflogname="profileCoverPhoto"]')
        )
        cover_image_url = d.execute_script("return arguments[0].getAttribute('src')", cover_image)
    except TimeoutError:
        pass

    return {
        "id": event_id,
        "title": title,
        "source": source,
        "cover_image_url": cover_image_url
    }


def extract_event_details(event_page: FetchedFbPageEvent) -> Dict[str, Any]:
    source = event_page["source"]

    start_timestamp, end_timestamp = extract_start_and_end_timestamps(source)
    event_object = extract_event_object(source)
    is_event_set = event_object["id"] != event_page["id"]

    return {
        "id": event_page["id"],
        "title": event_page["title"],
        "cover_image_url": event_page["cover_image_url"],
        "is_event_set": is_event_set,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "location": event_object["location"],
        "event_description": event_object["event_description"]["text"],
        "event_place": event_object["event_place"],
    }


def extract_start_and_end_timestamps(prerender: str) -> Tuple[int, Union[int, None]]:
    matches = [int(m.group(1)) for m in re.finditer('"current_start_timestamp":(\\d*)', prerender)]
    assert len(matches) == 1
    start_timestamp = matches[0]

    matches = [int(m.group(1)) for m in re.finditer('"end_timestamp":(\\d*)', prerender)]
    matches = [t for t in matches if t >= start_timestamp]

    if len(matches) == 0:
        return (start_timestamp, None)

    end_timestamp = min(matches, key=lambda t: t - start_timestamp)

    if end_timestamp == 0:
        end_timestamp = None

    return (start_timestamp, end_timestamp)


def extract_event_object(prerender: str) -> Dict[str, Any]:
    event_starts = [m.end() - 1 for m in re.finditer('"event":{', prerender)]

    events_objects = []
    for start in event_starts:
        try:
            events_objects.append(json.loads(prerender[start:]))
        except json.JSONDecodeError as err:
            if err.msg != "Extra data":
                raise err

            events_objects.append(json.loads(prerender[start:start+err.pos]))

    events_objects_with_location_and_event_description = [
        e for e in events_objects if "location" in e and "event_description" in e]

    assert len(events_objects_with_location_and_event_description) == 1
    event_object = events_objects_with_location_and_event_description[0]

    return event_object


"""
Convert event details to generic event
"""


class EventLocation(TypedDict):
    coordinates: Optional[Tuple[float, float]]
    city: Optional[str]
    country: Optional[str]
    contextual_name_or_adress: Optional[str]


class GenericEvent(TypedDict):
    source_url: str
    title: str
    description: str
    start_timestamp: int
    end_timestamp: Optional[int]
    location: Optional[EventLocation | Literal["online"]]
    cover_image_url: Optional[str]
    is_repeating_event: bool


def parse_event_details(dic: Dict[str, Any]) -> GenericEvent:
    return {
        "id": dic["id"],
        "source_url": f"https://www.facebook.com/events/{dic['id']}/",
        "title": dic["title"],
        "desctiption": dic["event_description"],
        "start_timestamp": dic["start_timestamp"],
        "end_timestamp": dic["end_timestamp"],
        "location": parse_event_location(dic),
        "cover_image_url": dic["cover_image_url"],
        "is_repeating_event": dic["is_event_set"],
    } # type: ignore


def parse_event_location(dic: Dict[str, Any]) -> Optional[EventLocation | Literal["online"]]:
    location = dic["location"] or {}
    place = dic["event_place"] or {}

    #if location is None:
        #assert failable_lookup(dic, "event_place", "location") is None
        #return "online"

    ret = {
        "address": failable_lookup(place, "address", "street"),
        "city": failable_lookup(place, "city", "contextual_name"),
        "contextual_name": failable_lookup(place, "city", "contextual_name"),
        "latitude": failable_lookup(place, "location", "latitude"),
        "longitude": failable_lookup(place, "location", "longitude"),
        "name": failable_lookup(place, "name"),
        "city-country": failable_lookup(location, "reverse_geocode", "city_page", "name"),
        "country_alpha2": failable_lookup(place, "location", "reverse_geocode", "country_alpha_two"),
        "place_url": failable_lookup(place, "url")
    }

    if ret["name"] == "Online event":
        return "online"

    return ret # type: ignore
    #return dic # type: ignore

K = TypeVar("K")

def failable_lookup(d: Dict[K, Any], *p: K) -> Any:
    key, *rest = p

    if not key in d:
        return None

    v = d[key]

    if rest == [] or v is None:
        return v

    return failable_lookup(v, *rest)
