
library(connectapi)
library(dplyr)
library(lubridate)
library(tidyr)

source("get_usage.R")

client <- connect()

dates <- list(
  from_date = today() - ddays(6),
  to_date = today()
)

CONTENT_GUID <- "f52ec842-3e95-4f9d-9f21-3c2e3c98b14d"

usage <- get_usage(client, dates$from_date, dates$to_date)

content <- get_content(client)
users <- get_users(client)

user_names <- users |>
  mutate(full_name = paste(first_name, last_name)) |>
  select(user_guid = guid, full_name, username)

# List of visits

usage |>
  filter(content_guid == CONTENT_GUID) |>
  left_join(user_names, by = "user_guid") |>
  replace_na(list(full_name = "[Anonymous]")) |>
  arrange(desc(timestamp)) |>
  select(timestamp, full_name, username)

# Aggregated visits

usage |>
  filter(content_guid == CONTENT_GUID) |>
  group_by(user_guid) |>
  summarize(n_visits = n()) |>
  left_join(user_names, by = "user_guid") |>
  replace_na(list(full_name = "[Anonymous]")) |>
  arrange(desc(n_visits)) |>
  select(full_name, username, n_visits)





