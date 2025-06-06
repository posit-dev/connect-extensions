box::use(
  grDevices[col2rgb],
  here[here],
  imola[
    breakpoint,
    breakpointSystem
  ],
  jsonlite[
    fromJSON,
    write_json
  ],
  stringr[
    fixed,
    str_replace_all
  ],
  yaml[read_yaml],
)

brand_path <- "_brand.yml"

charts_theme_template_path <- "app/metrics_theme_template.json"

#' @export
brand <- read_yaml(here(brand_path))

#' @export
is_credits_enabled <- isTRUE(brand$meta$credits$enabled)

# Breakpoint system for layout
#' @export
breakpoints <- breakpointSystem(
  "breakpoints",
  breakpoint("xs", min = 320),
  breakpoint("s", min = 428),
  breakpoint("m", min = 728),
  breakpoint("l", min = 1024),
  breakpoint("xl", min = 1200)
)

#' Mix two colors by transforming them to RGB
#' @param base_color Base color (hex)
#' @param blend_color Color to blend with (hex)
#' @param blend_weight Blend wiight in scale [0-1]
#' @return Mixed color hex
#' @export
color_mix <- function(base_color, blend_color, blend_weight) {
  # Get RGB values for each color [0–255]
  base_rgb <- col2rgb(base_color)[, 1]
  blend_rgb <- col2rgb(blend_color)[, 1]

  # Blend two colors based on the blend_weight [0–1]
  mixed_rgb <- round(base_rgb * (1 - blend_weight) + blend_rgb * blend_weight)

  # Format as hex color string
  sprintf("#%02X%02X%02X", mixed_rgb[1], mixed_rgb[2], mixed_rgb[3])
}

# Placeholder replacements for charts theme
#' @export
placeholder_replacements <- list(
  "$PRIMARY_LIGHT_COLOR" = color_mix(
    base_color = brand$color$palette[[brand$color$primary]],
    blend_color = brand$color$palette$white,
    blend_weight = 0.2
  ),
  "$BASE_FONT" = brand$typography$base,
  "$HEADINGS_FONT" = brand$typography$headings
)

#' Replace placeholders with values in given text
#' @param text Text containing placeholders in format "$PLACEHOLDER"
#' @param replacements List of placeholder names and their values
#' @return Text with values in place of placeholders
#' @export
replace_placeholders <- function(text, replacements) {
  for (key in names(replacements)) {
    text <- str_replace_all(text, fixed(key), as.character(replacements[[key]]))
  }
  text
}

#' Compose charts theme .json file using values from branding .yml file
#' @param brand_path Path to branding .yml file
#' @param template_path Path to charts theme template .json file
#' @return Path to charts theme .json file
#' @export
compose_charts_theme <- function(
  placeholder_replacements,
  template_path = charts_theme_template_path
) {
  if (!file.exists(template_path) ||
      length(placeholder_replacements) == 0 ||
      anyNA(placeholder_replacements)
  ) {
    return("")
  }

  # Read template and replace placeholders with values
  template_text <- readLines(template_path, warn = FALSE)
  updated_text <- replace_placeholders(
    text = template_text,
    replacements = placeholder_replacements
  )

  # Convert updated text to JSON and write output
  output_path <- sub("_template", "", template_path)
  theme <- fromJSON(paste(updated_text, collapse = "\n"), simplifyVector = TRUE)

  write_json(theme, output_path, pretty = TRUE, auto_unbox = TRUE)

  if (file.exists(output_path)) output_path else ""
}
