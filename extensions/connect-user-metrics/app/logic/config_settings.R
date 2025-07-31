box::use(
  config[get],
  magrittr[`%>%`],
  purrr[map, map_dfr],
  tibble[as_tibble, is_tibble],
)

box::use(
  app/logic/utils[AGG_LEVELS, AGG_TIME_LEVELS],
)

#' @export
split_yml_params <- function(param) {
  if (!is.list(param)) {
    if (is.null(param)) {
      return(NULL)
    }
    strsplit(param, ",", fixed = TRUE)[[1]] %>% map(trimws)
  } else {
    param %>% map_dfr(~ as_tibble(.x))
  }
}

#' It reads the config.yml file in the main app directory
#' If nothing or any error then it outputs NULL
#' @export
read_config_yml <- function(file_path = "config.yml") {
  tryCatch(
    {
      get(file = file_path) %>% map(split_yml_params)
    },
    error = function(e) {
      message("Error in parsing config")
      message(e)
      NULL
    }
  )
}


validate_apps <- function(config, data) {
  length_flag <- length(config$apps) == 0
  subset_flag <- all(config$apps %in% data)
  length_flag | subset_flag
}

validate_users <- function(config, data) {
  length_flag <- length(config$users) == 0
  subset_flag <- all(config$users %in% data)
  length_flag | subset_flag
}

validate_agg_levels <- function(config) {
  config$agg_levels %in% AGG_LEVELS
}

validate_agg_time <- function(config) {
  config$agg_time %in% AGG_TIME_LEVELS
}

validate_min_time <- function(config) {
  !is.na(as.POSIXlt(unlist(config$min_time), format = "%H:%M:%S"))
}

validate_goal <- function(config, goal_type) {
  if (goal_type %in% names(config)) {
    if (is_tibble(config[[goal_type]])) {
      return(nrow(config[[goal_type]]) > 0)
    } else {
      return(!is.na(as.numeric(config[[goal_type]])))
    }
  }
  FALSE
}

validate_week_start <- function(config) {
  if (is.null(config$week_start)) {
    return(FALSE)
  }

  dows <- c(
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday"
  )
  config$week_start %in% dows
}

#' @export
#'
#' Simple function to check whether a config param has a valid value or not
#'
#' @param config the config object after read_config_yml
#' @param config_key the key to validate against. Valid keys include apps,
#' users, agg_levels, min_time, unique_users_goal, sessions_goal
#' @param data if the validation rule needs some data object such as in apps,
#' users
#'
#' @return boolean result
is_config_valid <- function(config, config_key, data = NULL) {
  switch(config_key,
    apps = validate_apps(config, data),
    users = validate_users(config, data),
    agg_levels = validate_agg_levels(config),
    agg_time = validate_agg_time(config),
    min_time = validate_min_time(config),
    unique_users_goal = validate_goal(config, "unique_users_goal"),
    sessions_goal = validate_goal(config, "sessions_goal"),
    week_start = validate_week_start(config)
  )
}
