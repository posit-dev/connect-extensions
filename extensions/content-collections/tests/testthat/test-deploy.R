# Build a minimal configurator-layout root (root/dashboard_template + root/R)
# with the helpers stage_bundle insists on. Returns the root path; caller
# is responsible for unlink() on exit.
.make_config_root <- function() {
  root <- tempfile("configurator-")
  dir.create(file.path(root, "dashboard_template"), recursive = TRUE)
  dir.create(file.path(root, "R"))
  writeLines("---\ntitle: x\n---",
             file.path(root, "dashboard_template", "index.qmd"))
  writeLines("# render",      file.path(root, "R", "render.R"))
  writeLines("# icons",       file.path(root, "R", "icons.R"))
  writeLines("# connect_api", file.path(root, "R", "connect_api.R"))
  root
}

test_that("stage_bundle copies template files and writes collection.json", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  tmpl <- file.path(root, "dashboard_template")
  writeLines("dummy renv", file.path(tmpl, "renv.lock"))

  cfg <- list(title = "T", theme = "warm", source_type = "manual",
              guids = c("a", "b"))

  staged <- stage_bundle(template_dir = tmpl, config = cfg, source_dir = root)
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "index.qmd")))
  expect_true(file.exists(file.path(staged, "renv.lock")))
  expect_true(file.exists(file.path(staged, "collection.json")))

  written <- jsonlite::fromJSON(file.path(staged, "collection.json"),
                                simplifyVector = FALSE)
  expect_equal(written$title, "T")
  expect_equal(written$theme, "warm")
  expect_equal(written$guids, list("a", "b"))
})

test_that("stage_bundle errors clearly when template dir does not exist", {
  expect_error(
    stage_bundle(template_dir = "/nope/does/not/exist",
                 config = list(title = "T")),
    "template directory not found"
  )
})

test_that("stage_bundle drops .posit/ and renv build artifacts", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  tmpl <- file.path(root, "dashboard_template")
  writeLines("lock", file.path(tmpl, "renv.lock"))
  # Things that should be dropped
  dir.create(file.path(tmpl, ".posit", "publish"), recursive = TRUE)
  writeLines("stale", file.path(tmpl, ".posit", "publish", "old.toml"))
  dir.create(file.path(tmpl, "renv"))
  writeLines("source('renv/activate.R')", file.path(tmpl, "renv", "activate.R"))
  writeLines('{}', file.path(tmpl, "renv", "settings.json"))
  dir.create(file.path(tmpl, "renv", "library"))
  writeLines("binary", file.path(tmpl, "renv", "library", "leftover"))

  staged <- stage_bundle(template_dir = tmpl, config = list(title = "T"),
                         source_dir = root)
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "index.qmd")))
  expect_true(file.exists(file.path(staged, "renv.lock")))
  expect_true(file.exists(file.path(staged, "renv", "activate.R")))
  expect_true(file.exists(file.path(staged, "renv", "settings.json")))
  expect_false(dir.exists(file.path(staged, ".posit")))
  expect_false(dir.exists(file.path(staged, "renv", "library")))
})

test_that("stage_bundle copies R/render.R and R/icons.R into the bundle", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  staged <- stage_bundle(
    template_dir = file.path(root, "dashboard_template"),
    config       = list(title = "T"),
    source_dir   = root
  )
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "render.R")))
  expect_true(file.exists(file.path(staged, "icons.R")))
  expect_true(file.exists(file.path(staged, "index.qmd")))
})

test_that("stage_bundle copies www/icons/ into the bundle so cards can reference them", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  dir.create(file.path(root, "www", "icons"), recursive = TRUE)
  writeLines("<svg/>", file.path(root, "www", "icons", "quarto.svg"))
  writeLines("<svg/>", file.path(root, "www", "icons", "shiny.svg"))

  staged <- stage_bundle(
    template_dir = file.path(root, "dashboard_template"),
    config       = list(title = "T"),
    source_dir   = root
  )
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "icons", "quarto.svg")))
  expect_true(file.exists(file.path(staged, "icons", "shiny.svg")))
})

test_that("stage_bundle copies connect_api.R alongside render.R and icons.R", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  staged <- stage_bundle(
    template_dir = file.path(root, "dashboard_template"),
    config       = list(title = "T", source_type = "manual",
                        guids = character(0)),
    source_dir   = root
  )
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "connect_api.R")))
})

test_that("stage_bundle errors loudly when a required R/ helper is missing", {
  root <- tempfile("configurator-"); dir.create(root)
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  dir.create(file.path(root, "dashboard_template"))
  writeLines("---\ntitle: x\n---",
             file.path(root, "dashboard_template", "index.qmd"))
  # No R/ dir at all — silent skip would produce a corrupt bundle.
  expect_error(
    stage_bundle(
      template_dir = file.path(root, "dashboard_template"),
      config       = list(title = "T"),
      source_dir   = root
    ),
    "render\\.R"
  )
})

test_that("stage_bundle is independent of the process cwd when source_dir is given", {
  root <- .make_config_root()
  on.exit(unlink(root, recursive = TRUE), add = TRUE)
  # Move the process cwd somewhere with no R/ to prove source_dir resolves
  # the helpers regardless.
  elsewhere <- tempfile("elsewhere-"); dir.create(elsewhere)
  on.exit(unlink(elsewhere, recursive = TRUE), add = TRUE)
  old_wd <- setwd(elsewhere); on.exit(setwd(old_wd), add = TRUE)

  staged <- stage_bundle(
    template_dir = file.path(root, "dashboard_template"),
    config       = list(title = "T"),
    source_dir   = root
  )
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "render.R")))
  expect_true(file.exists(file.path(staged, "icons.R")))
  expect_true(file.exists(file.path(staged, "connect_api.R")))
})
