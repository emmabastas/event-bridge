from typing import *
import os
#import sys
import json
from flask import Flask
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import facebook
import util


app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello, world"


@app.route("/event/<int:event_id>", methods=["GET"])
def event(event_id: int):

    d = get_webdriver()

    event_page = util.memoize(
        "fb_page_event",
        util.curry(facebook.fetch_page__event)(d)
    )(str(event_id))

    event_details = facebook.extract_event_details(event_page)
    generic_event = facebook.parse_event_details(event_details)

    return generic_event


def get_webdriver() -> WebDriver:
    if "GOOGLE_CHROME_SHIM" in os.environ:
        cap = DesiredCapabilities.CHROME
        cap = {"binary_location": os.environ.get("GOOGLE_CHROME_SHIM")}
        driver = util.lazy_chrome_web_driver(desired_capabilities=cap)
        return driver

    return util.lazy_chrome_web_driver()


if __name__ == "__main__":
    app.run(debug=True)
