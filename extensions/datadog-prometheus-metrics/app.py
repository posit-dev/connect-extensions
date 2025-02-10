import datetime
import os
import time
import matplotlib.pyplot as plot
import pandas as pd
import streamlit as st
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v1.models import *

# grab the datadog API and application keys from environment variables
# app key requires the scope `timeseries_query` in order to query metrics
DATADOG_API_KEY = os.getenv("DD_API_KEY") 
DATADOG_APP_KEY = os.getenv("DD_APP_KEY") 

# configure the API client with credentials
configuration = Configuration()
configuration.api_key["apiKeyAuth"] = DATADOG_API_KEY
configuration.api_key["appKeyAuth"] = DATADOG_APP_KEY

# create metrics API client
api_client = ApiClient(configuration)
metrics_api = MetricsApi(api_client)

# define the prometheus queries available
queries = {
    "content_hits":"sum:prometheus.connect.content.hits.total{*}.as_count()",
    "queued_jobs":"sum:prometheus.connect.jobs.queue.total.jobs.in.queue{*}",
    "active_sessions":"sum:prometheus.connect.content.app.sessions.current{*}"
}

# create the dataframe and plot for results
df = pd.DataFrame(columns=["timestamp", "count"])
fig, ax = plot.subplots(figsize=(10, 5))

# configure plot settings that apply to all queries 
plot.xticks(rotation=45)
plot.grid(True)
plot.tight_layout()
ax.set_xlabel("Datetime")

# allow the user to select a prometheus metric to query
metric = st.selectbox("Metric to query: ", [ "Content Visits", "Queued Jobs", "Active Sessions" ])

# set the query and plot labels depending on the selected metric
if metric == "Content Visits":
    query = queries["content_hits"]
    ax.set_ylabel("Content Hits")
    ax.set_title("Content Hits Over Time")
elif metric == "Queued Jobs":
    query = queries["queued_jobs"]
    ax.set_ylabel("Jobs in Queue")
    ax.set_title("Jobs in Queue Over Time")
else:
    query = queries["active_sessions"] 
    ax.set_ylabel("Active App Sessions")
    ax.set_title("Active App Sessions Over Time")

# allow the user to select how many hours in the past we are querying
start = st.selectbox("Timeframe:", [ "Past 24H", "Past 12H", "Past 1H", "Past 30M" ])

# set the time now and calculate the from start time
end_time = int(datetime.datetime.now().timestamp())
if start == "Past 24H":
    start_time = end_time - (60 * 60 * 24) 
elif start == "Past 12H":
    start_time = end_time - (60 * 60 * 12) 
elif start == "Past 1H":
    start_time = end_time - (60 * 60) 
else:
    start_time = end_time - (60 * 30) 

# make the query 
response = metrics_api.query_metrics(
    _from=start_time,
    to=end_time,
    query=query
) 

# check if there is a series in the response
if response['series']:
    # iterate through series grabbing the list of points
    for series in response['series']:
        point_list = series['pointlist']
        # iterate through the points and add them to the dataframe
        for point in point_list:
            timestamp, count = point.value
            row = {"timestamp": timestamp, "count": count}
            df.loc[len(df)] = row
            
# convert from ms to datetime for displaying to user on plot
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

# feed the dataframe to the plot and style the plot
ax.plot(df["timestamp"], df["count"], marker="o", linestyle="-", color="purple")

# configure plot to show a little bit more space above the highest point
_, ymax = ax.get_ylim()
ax.set_ylim(bottom=0, top=ymax * 1.25)

# display the plot to the user
st.pyplot(fig)
