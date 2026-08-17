test_that("wizard_modal_dialog has step breadcrumb with current step bold", {
  modal <- wizard_modal_dialog(step = 2, mode = "create",
                               state = list(title = "T"),
                               body = shiny::tags$div("body"))
  html <- as.character(modal)
  expect_match(html, "1. Select content", fixed = TRUE)
  expect_match(html, "2. Describe",       fixed = TRUE)
  expect_match(html, "3. Theme",          fixed = TRUE)
  expect_match(html, "4. Preview",        fixed = TRUE)
  # Step 2 is current and should be bold (fw-bold class)
  expect_match(html, 'class="[^"]*fw-bold[^"]*"[^>]*>2\\. Describe', perl = TRUE)
})

test_that("wizard_modal_dialog header switches between create and edit modes", {
  m_create <- wizard_modal_dialog(step = 1, mode = "create",
                                  state = list(title = "Untitled"),
                                  body = shiny::tags$div())
  m_edit   <- wizard_modal_dialog(step = 1, mode = "edit",
                                  state = list(title = "My Coll"),
                                  body = shiny::tags$div())
  expect_match(as.character(m_create), "Add a content collection", fixed = TRUE)
  expect_match(as.character(m_edit),   "Edit collection: My Coll", fixed = TRUE)
})

test_that("wizard_modal_dialog footer shows Cancel + Next on step 1", {
  modal <- wizard_modal_dialog(step = 1, mode = "create",
                               state = list(), body = shiny::tags$div())
  html <- as.character(modal)
  expect_match(html, 'id="wizard_cancel"', fixed = TRUE)
  expect_match(html, 'id="wizard_next"',   fixed = TRUE)
  expect_no_match(html, 'id="wizard_back"', fixed = TRUE)
  expect_no_match(html, 'id="wizard_publish"', fixed = TRUE)
})

test_that("wizard_modal_dialog footer shows Back + Publish on step 4 (create)", {
  modal <- wizard_modal_dialog(step = 4, mode = "create",
                               state = list(), body = shiny::tags$div())
  html <- as.character(modal)
  expect_match(html, 'id="wizard_back"',    fixed = TRUE)
  expect_match(html, 'id="wizard_publish"', fixed = TRUE)
  expect_match(html, ">Publish<",           fixed = TRUE)
})

test_that("wizard footer renders Cancel as a link, ordered Cancel -> Back -> primary", {
  modal <- wizard_modal_dialog(step = 4, mode = "create",
                               state = list(), body = shiny::tags$div())
  html <- as.character(modal)
  cancel_pos  <- regexpr('id="wizard_cancel"',  html, fixed = TRUE)
  back_pos    <- regexpr('id="wizard_back"',    html, fixed = TRUE)
  primary_pos <- regexpr('id="wizard_publish"', html, fixed = TRUE)
  expect_true(cancel_pos < back_pos)
  expect_true(back_pos < primary_pos)
  # Cancel is a link button.
  expect_match(html,
    '<button[^>]*btn-link[^>]*id="wizard_cancel"',
    perl = TRUE)
})

test_that("wizard_modal_dialog footer says Update on step 4 (edit)", {
  modal <- wizard_modal_dialog(step = 4, mode = "edit",
                               state = list(title = "X"), body = shiny::tags$div())
  html <- as.character(modal)
  expect_match(html, ">Update<", fixed = TRUE)
})

test_that("wizard_modal_dialog uses tab nav (not breadcrumb) in edit mode", {
  modal <- wizard_modal_dialog(step = 1, mode = "edit",
                               state = list(title = "X"),
                               body = shiny::tags$div())
  html <- as.character(modal)
  # Tab buttons exist
  for (i in 1:4) {
    expect_match(html, sprintf('id="wizard_tab_%d"', i), fixed = TRUE)
  }
})

test_that("wizard_modal_dialog edit-mode footer shows only Cancel + Update", {
  modal <- wizard_modal_dialog(step = 1, mode = "edit",
                               state = list(title = "X"),
                               body = shiny::tags$div())
  html <- as.character(modal)
  expect_match(html, 'id="wizard_cancel"', fixed = TRUE)
  expect_match(html, 'id="wizard_publish"', fixed = TRUE)
  expect_match(html, ">Update<", fixed = TRUE)
  expect_no_match(html, 'id="wizard_back"', fixed = TRUE)
  expect_no_match(html, 'id="wizard_next"', fixed = TRUE)
})

test_that("wizard_modal_dialog edit-mode footer shows tab clicks even on step 4", {
  modal <- wizard_modal_dialog(step = 4, mode = "edit",
                               state = list(title = "X"),
                               body = shiny::tags$div())
  html <- as.character(modal)
  expect_match(html, 'id="wizard_tab_1"', fixed = TRUE)
  expect_match(html, ">Update<", fixed = TRUE)
})

test_that("the primary button is disabled when busy=TRUE", {
  modal <- wizard_modal_dialog(step = 4, mode = "edit",
                               state = list(title = "X"),
                               body = shiny::tags$div(),
                               busy = TRUE)
  html <- as.character(modal)
  # Attribute order on the rendered <button> isn't stable, so use
  # lookaheads to assert both `disabled` and `id="wizard_publish"`
  # appear inside the same <button ...> tag.
  expect_match(html,
    '<button(?=[^>]*disabled)(?=[^>]*id="wizard_publish")[^>]*>',
    perl = TRUE)
})

test_that("the primary button is NOT disabled by default", {
  modal <- wizard_modal_dialog(step = 4, mode = "edit",
                               state = list(title = "X"),
                               body = shiny::tags$div())
  html <- as.character(modal)
  # htmltools drops attributes whose value is FALSE/NA/NULL, so when
  # busy defaults to FALSE the `disabled` attribute is absent entirely.
  expect_no_match(html, "disabled", fixed = TRUE)
})
