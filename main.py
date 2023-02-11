from typing import *
import sys
import pprint
import facebook
import util
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


def main():
    ff_options = Options()
    ff_options.add_argument("-headless")
    driver = util.lazy_firefox_web_driver(options=ff_options)
    d = facebook.events_for_profile(driver, sys.argv[1])
    driver.quit()

    pp = pprint.PrettyPrinter(indent=2)
    #pp.pprint([e for e in d["prerenderdata"]])
    pp.pprint(d["events"])
    pp.pprint([(e["title"], e["location"]) for e in d["events"]])
    #pp.pprint([f'{e["id"]: <16} {e["name"]}\n{e["day_time_sentence"]}' for e in d["prerenderdata"]])
    #pp.pprint([f'{e["id"]: <16} {e["title"]}\n{e["start_timestamp"]}-{e["end_timestamp"]}' for e in d["events"] ])
    #pp.pprint(d["events"])


if __name__ == "__main__":
    main()
