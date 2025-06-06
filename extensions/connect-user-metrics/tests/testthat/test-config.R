box::use(
  magrittr[`%>%`],
  purrr[map],
  testthat,
  tibble[tibble],
  yaml[write_yaml],
)

box::use(
  app/logic/config_settings,
  app/logic/utils[AGG_LEVELS],
)

impl <- attr(config_settings, "namespace")

# all_params_present, check_config_data

raw_data <- list(
  apps = data.frame(guid = 1:3, title = c("app1", "app2", "app3")),
  users = data.frame(guid = 1:3, username = c("user1", "user2", "user3"))
)

testthat$context("Reading config file")
testthat$test_that("config.yml can be loaded and contains necessary inputs", {
  config1 <- list(
    default = list("apps" = "app1,app2", "users" = "user1,user2,user3", "agg_levels" = NULL)
  )
  dir.create("conf", recursive = TRUE)
  write_yaml(config1, file = "conf/config.yml")
  config <- config_settings$read_config_yml(file_path = "conf/config.yml")
  testthat$expect_true(inherits(config, "list"))
  testthat$expect_named(config, c("apps", "users", "agg_levels"))
})

testthat$test_that("Multiple parameters can be read", {
  config <- config_settings$read_config_yml(file_path = "conf/config.yml")
  testthat$expect_equal(config$apps, list("app1", "app2"))
  testthat$expect_equal(config$users, list("user1", "user2", "user3"))
  testthat$expect_null(config$agg_levels)
})

testthat$test_that("Wrong or missing yml is treated as NULL", {
  # Trying to read non-existent config.yml
  testthat$expect_error(
    config_settings$read_config_yml(file_path = "configuration.yml")
  ) # Misspelled file

  # Wrong config structure
  config2 <- list(custom = list())
  write_yaml(config2, "conf/config.yml")
  testthat$expect_error(config_settings$read_config_yml(file_path = "conf/config.yml"))

  unlink("conf/", recursive = TRUE)
})

testthat$context("Check config parameters")
testthat$test_that("All parameters values present in apps & users", {
  config <- list(
    default = list(
      "apps" = "app1,app2",
      "users" = "user1,user2,user3",
      "agg_levels" = "user_guid"
    )
  )
  config <- config$default %>% map(config_settings$split_yml_params)
  apps_check <- config_settings$is_config_valid(config, "apps", data = raw_data$apps$title)
  testthat$expect_true(apps_check)

  users_check <- config_settings$is_config_valid(config, "users", data = raw_data$users$username)
  testthat$expect_true(users_check)

  agg_check <- config_settings$is_config_valid(config, "agg_levels", data = AGG_LEVELS)
  testthat$expect_true(agg_check)
})

testthat$test_that("Parameter values not found in apps & users", {
  config <- list(
    default = list(
      "apps" = "app4,app5",
      "users" = "user4",
      "agg_levels" = "user_guid"
    )
  )
  config <- config$default %>% map(config_settings$split_yml_params)
  apps_check <- config_settings$is_config_valid(config, "apps", data = raw_data$apps$title)
  testthat$expect_false(apps_check)

  users_check <- config_settings$is_config_valid(config, "users", data = raw_data$users$username)
  testthat$expect_false(users_check)

  agg_check <- config_settings$is_config_valid(config, "agg_levels", data = AGG_LEVELS)
  testthat$expect_true(agg_check)
})

testthat$test_that("Not user parameter provided (Only apps & aggregation level)", {
  config <- list(
    default = list(
      "apps" = "app1,app2",
      "agg_levels" = "content_guid"
    )
  )
  config <- config$default %>% map(config_settings$split_yml_params)
  apps_check <- config_settings$is_config_valid(config, "apps", data = raw_data$apps$title)
  testthat$expect_true(apps_check)

  users_check <- config_settings$is_config_valid(config, "users", data = raw_data$users$username)
  testthat$expect_true(users_check)

  agg_check <- config_settings$is_config_valid(config, "agg_levels", data = AGG_LEVELS)
  testthat$expect_true(agg_check)
})

testthat$context("Validate config parameters")

testthat$test_that("validate_agg_time validates time levels correctly", {
  config <- list(agg_time = "day")
  testthat$expect_true(impl$validate_agg_time(config))

  config <- list(agg_time = "invalid_time")
  testthat$expect_false(impl$validate_agg_time(config))
})

testthat$test_that("validate_min_time validates time format correctly", {
  config <- list(min_time = "00:30:00")
  testthat$expect_true(impl$validate_min_time(config))

  config <- list(min_time = "invalid_time")
  testthat$expect_false(impl$validate_min_time(config))

  config <- list(min_time = "25:00:00") # Invalid hour
  testthat$expect_false(impl$validate_min_time(config))
})

testthat$test_that("validate_goal validates different goal types correctly", {
  # Numeric goal
  config <- list(unique_users_goal = "100")
  testthat$expect_true(impl$validate_goal(config, "unique_users_goal"))

  # Tibble goal
  config <- list(sessions_goal = tibble(
    date = c("2024-01-01", "2024-01-02"),
    goal = c(100, 200)
  ))
  testthat$expect_true(impl$validate_goal(config, "sessions_goal"))

  # Invalid numeric goal
  config <- list(unique_users_goal = "invalid")
  testthat$expect_warning(result <- impl$validate_goal(config, "unique_users_goal"))
  testthat$expect_false(result)

  # Empty tibble goal
  config <- list(sessions_goal = tibble())
  testthat$expect_false(impl$validate_goal(config, "sessions_goal"))

  # Missing goal
  config <- list()
  testthat$expect_false(impl$validate_goal(config, "sessions_goal"))
})

testthat$test_that("validate_week_start validates day names correctly", {
  config <- list(week_start = "monday")
  testthat$expect_true(impl$validate_week_start(config))

  config <- list(week_start = "sunday")
  testthat$expect_true(impl$validate_week_start(config))

  config <- list(week_start = "invalid_day")
  testthat$expect_false(impl$validate_week_start(config))

  config <- list(week_start = "MONDAY") # Case sensitive
  testthat$expect_false(impl$validate_week_start(config))

  config <- list(week_start = NULL)
  testthat$expect_false(impl$validate_week_start(config))

  config <- list(week_start = NA)
  testthat$expect_false(impl$validate_week_start(config))

  config <- list(week_start = "")
  testthat$expect_false(impl$validate_week_start(config))
})
