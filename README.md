# Description
Python webservice designed to run on Google Cloud AppEngine service. Each morning and evening it queries varies APIs to send travel alerts and weather forecasts to a Slack bot.

# Install
```
python3 -m venv travelenv
source travelenv/bin/activate
pip install -r src/requirements.txt
```
Optional for debugging/development
```
pip install -r debug/debug_requirements.txt
```

# Usage
Run `src/main.py` to start the flask webservice.
To trigger:
```
127.0.0.1:8080/morning_alerts
```
All REST end points are defined within `main.py`

# App engine update
To update codebase:
```
gcloud app deploy
```
To change cron jobs:
```
gcloud app deploy cron.yaml
```

# Example result
```
SAL to CLJ - 09:10, Exp:On time, Length:0
SAL to CLJ - 09:16, Exp:On time, Length:0
SAL to CLJ - 10:00, Exp:On time, Length:0
SAL to CLJ - 10:10, Exp:On time, Length:0

London Rd/A30: 24 mins
Weather at 2020-01-01 09:00:00+00:00:
No high winds
No bad weather: clear sky

Weather at 2020-01-01 18:00:00+00:00:
No high winds
No bad weather: few clouds
```