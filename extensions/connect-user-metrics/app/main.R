box::use(
  bslib,
  connectapi[connect, get_usage_shiny],
  dplyr,
  echarts4r[e_theme_register, echarts4rOutput, renderEcharts4r],
  here[here],
  lubridate,
  magrittr[`%>%`],
  mirai[mirai],
  reactable[reactableOutput, renderReactable],
  shiny,
  shinyWidgets[
    prettyCheckboxGroup,
    sendSweetAlert,
    updateCheckboxGroupButtons,
    updateVirtualSelect,
    virtualSelectInput
  ],
  shinyjs[toggleElement, useShinyjs],
  stats[setNames],
  tibble[add_row],
  tidyr[replace_na],
  yaml[read_yaml],
)

box::use(
  app/logic/aggregation[format_agg_usage, process_agg_usage],
  app/logic/charts,
  app/logic/config_settings[is_config_valid, read_config_yml],
  app/logic/data_utils,
  app/logic/duration_utils[format_duration],
  app/logic/ui_utils[
    brand,
    compose_charts_theme,
    is_credits_enabled,
    placeholder_replacements
  ],
  app/logic/utils[
    AGG_TIME_LEVELS,
    filter_data_by_user,
    get_app_titles,
    get_date_range_length_in_units,
    process_chart_goal,
    week_start_id
  ],
  app/view/footer,
  app/view/navbar_section,
  app/view/session_duration,
  app/view/table,
  app/view/ui_components[card_header_with_content, inline_info_text],
)

if (file.exists("app/constants/filter_users.yml")) {
  filter_users <- read_yaml(here("app/constants/filter_users.yml"))
} else {
  filter_users <- list()
  filter_users["users"] <- ""
}

# Read Config ----
config <- read_config_yml()

guids <- Sys.getenv("GUIDS", NA) |> data_utils$split_guids() # nolint: object_name_linter

#' @export
ui <- function(id) {
  ns <- shiny$NS(id)

  # Page with sidebar
  bslib$page_sidebar(
    useShinyjs(),
    shiny$useBusyIndicators(),
    title = navbar_section$ui(ns("navbar")),
    window_title = brand$meta$app_title,
    # Sidebar
    sidebar = bslib$sidebar(
      width = 300,
      padding = 30,
      open = "always",
      shiny$h5(shiny$tags$b("Filters")),
      shiny$uiOutput(ns("date_range_ui")),
      shiny$selectInput(
        inputId = ns("date_aggregation"), label = "Date aggregation",
        choices = c(
          "Daily" = "day",
          "Weekly" = "week",
          "Monthly" = "month"
        ),
        selected = "day",
        multiple = FALSE
      ),
      shiny$hr(),
      virtualSelectInput(
        inputId = ns("apps"),
        label = "Applications",
        choices = NULL,
        selected = NULL,
        multiple = TRUE,
        showValueAsTags = TRUE,
        width = "100%",
        dropboxWrapper = "body",
        noOfDisplayValues = 3
      ),
      prettyCheckboxGroup(
        inputId = ns("agg_levels"), label = "Aggregation level",
        choices = c(
          "Application" = "content_guid",
          "User" = "user_guid",
          "Date" = "start_date"
        ),
        selected = "start_date",
        icon = shiny$icon("check")
      ),
      session_duration$ui(ns("session_duration"), min_time = config$min_time),
      virtualSelectInput(
        inputId = ns("users"),
        label = "Users",
        choices = NULL,
        selected = NULL,
        multiple = TRUE,
        showValueAsTags = TRUE,
        width = "100%",
        dropboxWrapper = "body",
        noOfDisplayValues = 3
      ),
      if (is_credits_enabled) shiny$tags$footer(footer$ui())
    ),
    # Content
    shiny$div(
      e_theme_register(
        theme = compose_charts_theme(placeholder_replacements),
        name = "charts_theme"
      ),
      # Summary charts
      bslib$card(
        card_header_with_content(
          title = "Summary charts",
          content =
            shiny$div(
              class = "card-header-content",
              inline_info_text(
                "Average sessions: ", shiny$textOutput(ns("average_sessions")), NULL,
                "Average unique users: ", shiny$textOutput(ns("unique_users")), NULL
              )
            )
        ),
        bslib$layout_column_wrap(
          width = 1 / 2,
          echarts4rOutput(ns("plot")),
          echarts4rOutput(ns("unique_plot"))
        )
      ),
      shiny$hr(),
      # Summary table
      bslib$card(
        card_header_with_content(
          title = "Summary table",
          content = shiny$div(
            shiny$uiOutput(outputId = "ui_summary_table"),
            shiny$div(
              class = "card-header-content",
              inline_info_text(
                "Total sessions: ", shiny$textOutput(ns("total_sessions")),
                NULL,
                "Total unique users: ", shiny$textOutput(ns("total_unique_users")),
                NULL
              ),
              shiny$downloadButton(outputId = ns("agg_usage_download"), icon = NULL)
            )
          )
        ),
        reactableOutput(ns("agg_usage"))
      ),
      shiny$hr(),
      # Raw data
      bslib$card(
        card_header_with_content(
          title = "Raw Data",
          content = shiny$div(
            class = "card-header-content",
            inline_info_text(
              "Most active app: ", shiny$textOutput(ns("most_active_app")), NULL,
              "Most active user: ", shiny$textOutput(ns("most_active_user")), NULL
            ),
            shiny$downloadButton(ns("raw_usage_download"), icon = NULL)
          )
        ),
        reactableOutput(ns("raw_usage"))
      )
    )
  )
}

#' @export
server <- function(id) {
  shiny$moduleServer(id, function(input, output, session) {
    # navbar ------------------------------------------------------------------
    navbar_section$server("navbar")

    if (!is.null(config)) {
      ## Config: Agg Levels ----
      if (is_config_valid(config, "agg_levels")) {
        updateCheckboxGroupButtons(
          session, "agg_levels",
          selected = config$agg_levels
        )
      }

      ## Config: Agg Time ----
      if (is_config_valid(config, "agg_time")) {
        selected_agg_time <- unlist(config$agg_time)
        names(selected_agg_time) <- names(which(
          AGG_TIME_LEVELS == selected_agg_time
        ))

        updateVirtualSelect(
          inputId = "date_aggregation", selected = unname(selected_agg_time),
          session = session
        )
      }
    }

    # Connection with client ---------------------------------------------------
    client <- shiny$reactive({
      tryCatch(
        connect(),
        error = function(err) {
          sendSweetAlert(
            session,
            title = "Could not establish connection to RStudio Connect",
            text = err$message,
            type = "error",
            btn_labels = "Close"
          )
        }
      )
    })

    # rendering DateRangeInput with correct range -----------------------------
    output$date_range_ui <- shiny$renderUI({
      shiny$req(apps_guids())

      max_date <-
        data_utils$get_latest_date_from_client(
          client = client(),
          guids = apps_guids()
        )

      min_date <- max_date - lubridate$days(30)

      shiny$dateRangeInput(
        inputId = session$ns("date_range"), label = "Date range",
        format = "dd M yyyy", separator = "→",
        start = min_date, end = max_date,
        weekstart = ifelse(week_start_id == 7, 0, week_start_id)
      )
    })

    # Fetching data from client -----------------------------------------------
    apps <- shiny$reactive({
      apps <-
        data_utils$get_apps_from_client(client = client(), guids = guids) |>
        dplyr$select(guid, name, title)

      # intersect with provided guids, if any
      if (!is.null(guids)) {
        apps <- apps |> dplyr$filter(guid %in% guids)
      }

      apps
    })

    # get data only for
    apps_guids <- shiny$reactive({
      shiny$req(apps())

      apps()$guid
    })

    users <- shiny$reactive({
      data_utils$get_users_from_client(client = client()) |>
        dplyr$select(guid, username) %>%
        add_row(guid = "unknown", username = "unknown") %>%
        filter_data_by_user(filter_users$users)
    })

    # async fetch of usage data -----------------------------------------------
    task_usage <- shiny$ExtendedTask$new(
      function(...) {
        mirai(
          {
            get_usage_shiny(
              client,
              limit = Inf, content_guid = guids,
              from = from, to = to
            )
          },
          ...
        )
      }
    )

    shiny$observe({
      shiny$req(input$date_range)
      date_range <- input$date_range

      # add  `+ lubridate$days(1)` in `to` to get data from the whole day;
      task_usage$invoke(
        client = client(), guids = apps_guids(),
        from = date_range[1], to = date_range[2] + lubridate$days(1),
        get_usage_shiny = get_usage_shiny
      )
    })

    raw_usage <- shiny$reactive({
      task_usage$result()
    })

    # Usage + joins -----------------------------------------------------------
    joined_usage <- shiny$reactive({
      shiny$req(apps())
      shiny$req(users())
      shiny$req(raw_usage())

      raw_usage() |>
        replace_na(list(user_guid = "unknown")) |>
        dplyr$left_join(apps(), by = c("content_guid" = "guid")) |>
        dplyr$left_join(users(), by = c("user_guid" = "guid")) |>
        dplyr$mutate(
          duration = as.double(ended - started, units = "secs"),
          start_date = as.Date(started)
        ) |>
        filter_data_by_user(filter_users$users)
    })

    rc_min_time <- session_duration$server("session_duration")

    usage <- shiny$reactive({
      shiny$req(joined_usage())

      joined_usage() |>
        # filter by selected users and apps
        dplyr$filter(content_guid %in% input$apps, user_guid %in% input$users) |>
        dplyr$filter(duration >= rc_min_time())
    })

    # Set API Response as Choices ----
    shiny$observe({
      apps_choices <- apps() %>%
        dplyr$filter(!is.na(guid)) %>%
        # Use application name if it doesn't have title
        dplyr$mutate(display_title = get_app_titles(title, name)) %>%
        {
          setNames(.$guid, .$display_title)
        }

      users_choices <- users() %>%
        dplyr$filter(!is.na(guid), !is.na(username)) %>%
        {
          setNames(.$guid, .$username)
        }

      updateVirtualSelect(
        inputId = "apps", choices = apps_choices, selected = unname(apps_choices),
        session = session
      )

      updateVirtualSelect(
        inputId = "users", choices = users_choices, selected = unname(users_choices),
        session = session
      )
    })

    agg_usage <- shiny$reactive({
      process_agg_usage(
        usage = usage(),
        agg_levels = input$agg_levels,
        date_aggregation = input$date_aggregation,
        apps = apps(),
        users = users()
      )
    })

    shiny$observe({
      toggleElement("unauthenticated_disclaimer", condition = "user_guid" %in% input$agg_levels)
    })

    formatted_usage <- shiny$reactive({
      usage() %>%
        dplyr$mutate(duration = format_duration(duration)) %>%
        dplyr$select(
          Application = title,
          Username = username,
          "Session start" = started,
          "Session end" = ended,
          "Session duration" = duration
        )
    })


    # Raw data display ----
    output$most_active_app <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      names(which.max(table(formatted_usage()$Application)))
    })

    output$most_active_user <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      names(which.max(table(formatted_usage()$Username)))
    })

    # Render reactables -------------------------------------------------------
    output$raw_usage <- renderReactable({
      formatted_usage() %>%
        table$reactable2()
    })

    output$raw_usage_download <- shiny$downloadHandler(
      "User Metrics (raw data).csv",
      function(file) data_utils$write_csv(formatted_usage(), file)
    )

    formatted_agg_usage <- shiny$reactive({
      format_agg_usage(agg_usage(), input$date_aggregation, format_duration)
    })

    output$agg_usage <- renderReactable({
      formatted_agg_usage() %>%
        table$reactable2()
    })

    ## Config: Sessions Goal ----
    sessions_goal <- NULL
    if (is_config_valid(config, "sessions_goal")) {
      sessions_goal <- config$sessions_goal
    }

    ## Config: Unique Users Goal ----
    unique_users_goal <- NULL
    if (is_config_valid(config, "unique_users_goal")) {
      unique_users_goal <- config$unique_users_goal
    }

    # Summary charts ----
    date_diff_in_units <- shiny$reactive({
      get_date_range_length_in_units(
        input$date_range[1],
        input$date_range[2],
        input$date_aggregation
      )
    })

    output$average_sessions <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      nrow(formatted_usage()) / date_diff_in_units()
    })

    output$unique_users <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      length(unique(formatted_usage()$`Username`)) / date_diff_in_units()
    })

    output$plot <- renderEcharts4r({
      sessions_goal <- process_chart_goal(
        sessions_goal,
        input$agg_levels,
        input$date_aggregation
      )

      shiny$validate(
        shiny$need(
          nrow(agg_usage()) > 0, "No data to display."
        )
      )

      charts$plot_session_chart(
        agg_usage(),
        input$agg_levels,
        input$date_range,
        input$date_aggregation,
        sessions_goal
      )
    })

    output$unique_plot <- renderEcharts4r({
      unique_users_goal <- process_chart_goal(
        unique_users_goal,
        input$agg_levels,
        input$date_aggregation
      )

      shiny$validate(
        shiny$need(
          nrow(agg_usage()) > 0, "No data to display."
        )
      )

      charts$plot_unique_chart(
        agg_usage(),
        input$agg_levels,
        input$date_range,
        input$date_aggregation,
        unique_users_goal
      )
    })

    # Summary table ----
    output$total_sessions <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      nrow(formatted_usage())
    })

    output$total_unique_users <- shiny$renderText({
      shiny$validate(
        shiny$need(
          nrow(formatted_usage()) > 0, "No data to display."
        )
      )

      length(unique(formatted_usage()$`Username`))
    })

    output$agg_usage_download <- shiny$downloadHandler(
      "User Metrics (aggregated data).csv",
      function(file) data_utils$write_csv(formatted_agg_usage(), file)
    )

    if (!is.null(config)) {
      ## Config: Apps ----
      shiny$observeEvent(is_config_valid(config, "apps", apps()$title), {
        selected_apps <- NULL
        if (length(unlist(config$apps)) == 0) {
          selected_apps <- apps()$guid
          # Use application name if it doesn't have title
          names(selected_apps) <- get_app_titles(apps()$title, apps()$name)
        } else {
          selected_app_names <- unlist(config$apps)
          selected_apps <-
            apps()[apps()$title %in% selected_app_names, ]$guid
          names(selected_apps) <- selected_app_names
        }

        updateVirtualSelect(
          inputId = "apps", selected = unname(selected_apps),
          choices = selected_apps,
          session = session
        )
      })

      ## Config: Users ----
      shiny$observeEvent(is_config_valid(config, "users", users()$username), {
        selected_users <- NULL
        if (length(unlist(config$users)) == 0) {
          selected_users <- users()$guid
          names(selected_users) <- users()$username
        } else {
          selected_user_names <- unlist(config$users)
          selected_users <-
            users()[users()$username %in% selected_user_names, ]$guid
          names(selected_users) <- selected_user_names
        }

        updateVirtualSelect(
          inputId = "users", selected = unname(selected_users),
          choices = selected_users,
          session = session
        )
      })
    }
  })
}
