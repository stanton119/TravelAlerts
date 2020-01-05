from flask import Flask
import numpy as np
import requests
import json
import math
import pytz
import datetime

from private import *  # Stores API keys and default locations

# Trains #
def check_next_train(station_from: str = "CLJ", station_to: str = "WAT") -> str:
    # Replace with the correct URL
    url = (
        f"https://huxley.apphb.com/departures/{station_from}"
        + f"/to/{station_to}/5?accessToken={HUXLEY_TOKEN}"
    )
    response = requests.get(url)

    # For successful API call, response code will be 200 (OK)
    if response.ok:

        # Load response into JSON
        json_data = json.loads(response.content)

        if "trainServices" in json_data:
            trains = json_data["trainServices"]
            if trains is not None:
                out_string = ""
                for k in range(0, min(len(trains), 4)):
                    out_string = out_string + (
                        "{} to {} - {}, Exp:{}, Length:{}".format(
                            station_from,
                            station_to,
                            trains[k]["std"],
                            trains[k]["etd"],
                            trains[k]["length"],
                        )
                        + "\n"
                    )
            else:
                out_string = "No trains found " + station_from + " to " + station_to
        else:
            out_string = "No trains found " + station_from + " to " + station_to
        return out_string
    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()
        return "check_next_train failed"


def morning_trains() -> str:
    train_str = check_next_train(station_from=STATION_HOME, station_to=STATION_WORK)
    return train_str


def evening_trains() -> str:
    train_str = check_next_train(station_from=STATION_WORK, station_to=STATION_HOME)
    return train_str


# Traffic #
def get_travel_time(
    station_from: str = TRAFFIC_HOME, station_to: str = TRAFFIC_WORK
) -> str:
    # Form google api url
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={station_from}&destination={station_to}&departure_time=now&traffic_model=best_guess&key={TRAFFIC_API_KEY}"
    response = requests.get(url)

    # For successful API call, response code will be 200 (OK)
    if response.ok:
        # Load response into JSON
        json_data = json.loads(response.content)
        try:
            return (
                json_data["routes"][0]["summary"]
                + ": "
                + json_data["routes"][0]["legs"][0]["duration_in_traffic"]["text"]
            )
        except:
            return "Error getting route"
    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()
        return "get_travel_time failed"


# Weather #
def get_weather_ref_time(hour_ref: int = 18) -> int:
    local = pytz.timezone("Europe/London")

    # Get reference times in UTC
    ref_date = datetime.datetime.now()
    time_ref = ref_date.replace(hour=hour_ref, minute=0, second=0, microsecond=0)

    # Default to next day if already past
    if time_ref < datetime.datetime.now():
        time_ref = time_ref.replace(day=time_ref.day + 1)

    # Convert to UTC timezone
    time_ref = local.localize(time_ref).astimezone(pytz.utc)
    # Convert to same date int format
    return int(time_ref.timestamp())


def get_local_datetime(timestamp: int) -> str:
    local = pytz.timezone("Europe/London")

    # Get reference times in UTC
    ref_date = datetime.datetime.fromtimestamp(timestamp)

    # Convert to UTC timezone
    return str(local.localize(ref_date))


def find_closest_timestamp(weather_data, time_ref: int):
    # Returns json object with closest time stamp
    time_diffs = np.infty
    for forecast in weather_data:
        if np.abs(time_ref - forecast["dt"]) < time_diffs:
            weather_data_closest = forecast
            time_diffs = np.abs(time_ref - forecast["dt"])
    return weather_data_closest


def process_weather_response(weather_data, hour_ref: int) -> str:
    # Check weather between
    # Temp in Kelvin -273.15
    # Convert time (dt) into datetime, check time for 9am/6pm
    time_ref = get_weather_ref_time(hour_ref)
    print(time_ref)
    forecast = find_closest_timestamp(weather_data, time_ref=time_ref)

    out_string = "Weather at {}:\n".format(get_local_datetime(forecast["dt"]))
    # Should probably flag is anything today is rain/wind

    # Check wind >~30km/h
    if forecast["wind"]["speed"] > 8:
        out_string += "High winds: {}".format(forecast["wind"]["speed"])
    else:
        out_string += "No high winds"

    # Check rain
    if math.floor(forecast["weather"][0]["id"] / 100) in [2, 3, 5, 6]:
        out_string += "\nWeather: {}".format(forecast["weather"][0]["description"])
    else:
        out_string += "\nNo bad weather: {}".format(
            forecast["weather"][0]["description"]
        )
    return out_string


def get_weather(latitude: float, longitude: float, hour_ref: int = 18) -> str:
    # Get rain and wind at 9am/6pm in a given location
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&APPID={WEATHER_API_KEY}"

    response = requests.get(url)

    # For successful API call, response code will be 200 (OK)
    if response.ok:
        # Load response into JSON
        json_data = json.loads(response.content)
        try:
            weather_data = json_data["list"]
            if len(weather_data) > 0:
                out_string = process_weather_response(weather_data, hour_ref)
            else:
                out_string = "No weather found"
            return out_string
        except:
            return "Weather update failed"
    else:
        # If response code is not ok (200), print the resulting http error code with description
        response.raise_for_status()
        return "get_weather failed"


# Others #
send_slack_on = 1


def send_slack(message: str):
    base_url = "https://hooks.slack.com/services/"
    webhook = SLACK_WEBHOOK

    url = base_url + webhook
    payload = '{"text":"' + message + '"}'

    headers = {"Content-type": "application/json"}
    try:
        r = requests.post(url, payload, headers=headers)
        return "Message sent", r
    except:
        return "Failed"


# Setup as webservice
app = Flask(__name__)


@app.route("/morning_alerts")
def morning_alerts():
    if send_slack_on:
        send_slack(morning_trains())
        send_slack(get_travel_time())
        send_slack(
            get_weather(hour_ref=9, latitude=WEATHER_LAT, longitude=WEATHER_LONG)
        )
        send_slack(
            get_weather(hour_ref=18, latitude=WEATHER_LAT, longitude=WEATHER_LONG)
        )
    else:
        print(morning_trains())
        print(get_travel_time())
        print(get_weather(hour_ref=9, latitude=WEATHER_LAT, longitude=WEATHER_LONG))
        print(get_weather(hour_ref=18, latitude=WEATHER_LAT, longitude=WEATHER_LONG))
    return "Morning alerts finish", 200


@app.route("/evening_train_alerts")
def evening_train_alerts():
    if send_slack_on:
        send_slack(evening_trains())
    else:
        print(evening_trains())
    return "Evening trains finish", 200


@app.route("/evening_weather")
def evening_weather():
    if send_slack_on:
        send_slack(
            get_weather(hour_ref=18, latitude=WEATHER_LAT, longitude=WEATHER_LONG)
        )
    else:
        print(get_weather(hour_ref=18, latitude=WEATHER_LAT, longitude=WEATHER_LONG))
    return "Evening weather finish", 200


if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)

