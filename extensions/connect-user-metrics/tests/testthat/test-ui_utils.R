box::use(
  jsonlite[fromJSON],
  testthat[
    expect_equal,
    expect_match,
    expect_true,
    expect_type,
    test_that
  ],
  withr[with_tempdir],
  yaml[read_yaml],
)

box::use(
  app/logic/ui_utils,
)

black <- "#000000"
white <- "#FFFFFF"
gray  <- "#808080"

test_that("color_mix returns hex color", {
  ui_utils$color_mix(black, white, 0.2) |>
    expect_type("character") |>
    expect_match("#")
})

test_that("color_mix returns base color when weight is 0", {
  expect_equal(
    ui_utils$color_mix(black, white, 0),
    black
  )
})

test_that("color_mix returns blend color when weight is 1", {
  expect_equal(
    ui_utils$color_mix(black, white, 1),
    white
  )
})

test_that("color_mix returns gray when white and black are mixed in same equally", {
  expect_equal(
    ui_utils$color_mix(black, white, 0.5),
    gray
  )
})

test_that("replace_placeholders replaces single placeholder", {
  input <- "color: $COLOR"
  replacements <- list("$COLOR" = black)

  expect_equal(
    ui_utils$replace_placeholders(input, replacements),
    "color: #000000"
  )
})

test_that("replace_placeholders replaces multiple placeholders", {
  input <- "font: $FONT, color: $COLOR"
  replacements <- list(
    "$FONT" = "Roboto",
    "$COLOR" = black
  )

  expect_equal(
    ui_utils$replace_placeholders(input, replacements),
    "font: Roboto, color: #000000"
  )
})

test_that("replace_placeholders is not replacing placeholders if no matches", {
  input <- "Text with $PLACEHOLDER"

  replacements <- list(
    "$NAME" = "Test"
  )
  expect_equal(
    ui_utils$replace_placeholders(input, replacements),
    "Text with $PLACEHOLDER"
  )

  replacements <- list()
  expect_equal(
    ui_utils$replace_placeholders(input, replacements),
    "Text with $PLACEHOLDER"
  )
})

test_that("replace_placeholders replaces across multiple lines", {
  input <- c(
    "{",
    "  \"color\": \"$COLOR\",",
    "  \"font\": \"$FONT\"",
    "}"
  )

  replacements <- list(
    "$COLOR" = black,
    "$FONT" = "Roboto"
  )

  expect_equal(
    ui_utils$replace_placeholders(input, replacements),
    c(
      "{",
      "  \"color\": \"#000000\",",
      "  \"font\": \"Roboto\"",
      "}"
    )
  )
})

test_that("compose_charts_theme returns '' when there is no replacements or template file", {
  expect_equal(
    ui_utils$compose_charts_theme(
      placeholder_replacements = NULL,
      template_path = "app/test_template.json"
    ),
    ""
  )

  expect_equal(
    ui_utils$compose_charts_theme(
      placeholder_replacements = NA,
      template_path = "app/test_template.json"
    ),
    ""
  )

  expect_equal(
    ui_utils$compose_charts_theme(
      placeholder_replacements = list(),
      template_path = "app/test_template.json"
    ),
    ""
  )

  expect_equal(
    ui_utils$compose_charts_theme(
      placeholder_replacements = list(
        "$TEST" = "test",
      ),
      template_path = "app/test_template.json"
    ),
    ""
  )

  expect_equal(
    ui_utils$compose_charts_theme(
      placeholder_replacements = list(),
      template_path = "app/metrics_theme_template.json"
    ),
    ""
  )
})

test_that("compose_charts_theme returns path to charts theme and replaces placeholders with values from brand file", { #nolint line_length_linter
  with_tempdir(
    {
      brand_path <- "test_brand.yml"
      template_path <- "test_template.json"
      output_path <- sub("_template", "", template_path)
      expected_theme_path <- "expected_theme.json"

      # Minimal valid branding file
      writeLines(
        c(
          "color:",
          "  palette:",
          "    black: \"#000000\"",
          "  primary: black"
        ),
        brand_path
      )

      # Minimal valid charts theme template file
      writeLines(
        c(
          "{",
          "    \"color\": \"$PRIMARY_COLOR\"",
          "}"
        ),
        template_path
      )

      # Expected charts theme file
      writeLines(
        c(
          "{",
          "    \"color\": \"#000000\"",
          "}"
        ),
        expected_theme_path
      )

      brand <- read_yaml(brand_path)
      placeholder_replacements <- list(
        "$PRIMARY_COLOR" = brand$color$palette[[brand$color$primary]]
      )

      chart_theme_path <- ui_utils$compose_charts_theme(
        placeholder_replacements = placeholder_replacements,
        template_path = template_path
      )

      expect_true(file.exists(chart_theme_path))

      expect_equal(
        chart_theme_path,
        output_path
      )

      expect_equal(
        fromJSON(chart_theme_path),
        fromJSON(expected_theme_path)
      )
    }
  )
})
