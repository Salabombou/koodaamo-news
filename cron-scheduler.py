from datetime import datetime, timedelta
import http.client
import urllib.parse
import json
import time
import os

from typing import List, Tuple


def yle_news() -> List[Tuple[str, datetime, datetime]]:
    date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "yleReferer": f"tv.guide.{date}.tv_opas.yle_tv1.untitled_list",
        "language": "fi",
        "v": "10",
        "client": "yle-areena-web",
        "offset": "0",
        "limit": "100",
        "country": "FI",
        "isPortabilityRegion": "true",
        "app_id": "areena-web-items",
        "app_key": "wlTs5D9OjIdeS9krPzRQR4I1PYVzoazN",
    }
    query = urllib.parse.urlencode(params)

    conn = http.client.HTTPSConnection("areena.api.yle.fi")
    conn.request("GET", f"/v1/ui/schedules/yle-tv1/{date}.json?{query}")
    response = conn.getresponse()

    programs = json.loads(response.read())["data"]

    news_program_uris = ["yleareena://items/1-3235352", "yleareena://items/1-50865561"]
    news_programs = []
    for program in programs:
        program_series_uri = None
        for label in program["labels"]:
            if label["type"] == "seriesLink":
                program_series_uri = label["pointer"]["uri"]
                break

        if program_series_uri in news_program_uris:
            news_programs.append(program)

    cronjobs = []
    for program in news_programs:
        start_time = datetime.fromisoformat(program["labels"][0]["raw"])
        end_time = datetime.fromisoformat(program["labels"][1]["raw"])

        cronjobs.append(["yle", start_time, end_time])

    return cronjobs


def mtv3_news() -> List[Tuple[str, datetime, datetime]]:
    date = datetime.now().strftime("%Y%m%d")

    conn = http.client.HTTPSConnection("st.mtvuutiset.fi")
    conn.request("GET", f"/asset/data/kanavaopas/tvopas-{date}-lite.json")
    response = conn.getresponse()

    programs = json.loads(response.read())

    news_programs = []
    for program in programs:
        if not {"program_type", "name", "start_time", "end_time"}.issubset(program):
            continue
        elif program["program_type"] != "uutiset":
            continue
        elif "Uutiset" not in program["name"]:
            continue
        elif "Live" in program["name"]:
            continue
        news_programs.append(program)

    cronjobs = []
    for program in news_programs:
        start_time = datetime.fromtimestamp(program["start_time"])
        end_time = datetime.fromtimestamp(program["end_time"])

        cronjobs.append(["mtv3", start_time, end_time])

    return cronjobs


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:00")
    error = None
    for _ in range(5):
        try:
            cronjobs = ["* * * * * python cron-scheduler.py\n"]
            schedule = {"yle": [], "mtv3": []}

            news = [*yle_news(), *mtv3_news()]

            for [source, start_time, end_time] in news:
                start_second = start_time.second
                start_minute = start_time.minute
                start_hour = start_time.hour

                duration = (end_time - start_time).seconds

                cronjobs.append(
                    f"{start_minute:02} {start_hour:02} * * * /bin/sh record-news.sh {source} {start_second} {duration}\n"
                )
                schedule[source].append(
                    {
                        "start_time": start_time.strftime("%H:%M:%S"),
                        "end_time": end_time.strftime("%H:%M:%S"),
                    }
                )

            with open("/tmp/cronjobs", "w") as f:
                f.write("\n".join(cronjobs))

            with open("/tmp/schedule.json", "w") as f:
                json.dump(schedule, f, indent=2)

            if os.path.isdir("/vods"):
                os.system("crontab /tmp/cronjobs")
                os.system("cp /tmp/schedule.json /vods/schedule.json")
                print(f"{timestamp} Updated cronjobs")
            break
        except Exception as e:
            print(f"{timestamp} {e}")
            error = e
            time.sleep(5)
            continue
    else:
        print(f"{timestamp} Failed to update cronjobs")
        raise error


if __name__ == "__main__":
    main()
