test_that("stage_bundle copies template files and writes collection.json", {
  tmpl <- tempfile(); dir.create(tmpl)
  writeLines("---\ntitle: x\n---", file.path(tmpl, "index.qmd"))
  writeLines("dummy renv", file.path(tmpl, "renv.lock"))

  cfg <- list(title = "T", theme = "warm", source_type = "manual",
              guids = c("a", "b"))

  staged <- stage_bundle(template_dir = tmpl, config = cfg)
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
  tmpl <- tempfile(); dir.create(tmpl)
  writeLines("---\ntitle: x\n---", file.path(tmpl, "index.qmd"))
  writeLines("lock", file.path(tmpl, "renv.lock"))
  # Things that should be dropped
  dir.create(file.path(tmpl, ".posit", "publish"), recursive = TRUE)
  writeLines("stale", file.path(tmpl, ".posit", "publish", "old.toml"))
  dir.create(file.path(tmpl, "renv"))
  writeLines("source('renv/activate.R')", file.path(tmpl, "renv", "activate.R"))
  writeLines('{}', file.path(tmpl, "renv", "settings.json"))
  dir.create(file.path(tmpl, "renv", "library"))
  writeLines("binary", file.path(tmpl, "renv", "library", "leftover"))

  staged <- stage_bundle(template_dir = tmpl, config = list(title = "T"))
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "index.qmd")))
  expect_true(file.exists(file.path(staged, "renv.lock")))
  expect_true(file.exists(file.path(staged, "renv", "activate.R")))
  expect_true(file.exists(file.path(staged, "renv", "settings.json")))
  expect_false(dir.exists(file.path(staged, ".posit")))
  expect_false(dir.exists(file.path(staged, "renv", "library")))
})

test_that("stage_bundle copies R/render.R and R/icons.R into the bundle", {
  # Build a fake configurator project layout in tmp
  config_root <- tempfile("configurator-")
  dir.create(file.path(config_root, "dashboard_template"), recursive = TRUE)
  dir.create(file.path(config_root, "R"))
  writeLines("---\ntitle: x\n---", file.path(config_root, "dashboard_template", "index.qmd"))
  writeLines("# render", file.path(config_root, "R", "render.R"))
  writeLines("# icons",  file.path(config_root, "R", "icons.R"))

  # Run stage_bundle from the configurator root so the relative R/ path resolves
  old_wd <- setwd(config_root); on.exit(setwd(old_wd), add = TRUE)
  staged <- stage_bundle(template_dir = "dashboard_template",
                         config = list(title = "T"))
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "render.R")))
  expect_true(file.exists(file.path(staged, "icons.R")))
  expect_true(file.exists(file.path(staged, "index.qmd")))
})

test_that("stage_bundle copies www/icons/ into the bundle so cards can reference them", {
  config_root <- tempfile("configurator-")
  dir.create(file.path(config_root, "dashboard_template"), recursive = TRUE)
  dir.create(file.path(config_root, "R"))
  dir.create(file.path(config_root, "www", "icons"), recursive = TRUE)
  writeLines("---\ntitle: x\n---",
             file.path(config_root, "dashboard_template", "index.qmd"))
  writeLines("# render", file.path(config_root, "R", "render.R"))
  writeLines("# icons",  file.path(config_root, "R", "icons.R"))
  writeLines("<svg/>",   file.path(config_root, "www", "icons", "quarto.svg"))
  writeLines("<svg/>",   file.path(config_root, "www", "icons", "shiny.svg"))

  old_wd <- setwd(config_root); on.exit(setwd(old_wd), add = TRUE)
  staged <- stage_bundle(template_dir = "dashboard_template",
                         config = list(title = "T"))
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "icons", "quarto.svg")))
  expect_true(file.exists(file.path(staged, "icons", "shiny.svg")))
})

test_that("stage_bundle copies connect_api.R alongside render.R and icons.R", {
  config_root <- tempfile("configurator-")
  dir.create(file.path(config_root, "dashboard_template"), recursive = TRUE)
  dir.create(file.path(config_root, "R"))
  writeLines("---\ntitle: T\n---", file.path(config_root, "dashboard_template", "index.qmd"))
  writeLines("# render",      file.path(config_root, "R", "render.R"))
  writeLines("# icons",       file.path(config_root, "R", "icons.R"))
  writeLines("# connect_api", file.path(config_root, "R", "connect_api.R"))

  old_wd <- setwd(config_root); on.exit(setwd(old_wd), add = TRUE)
  cfg <- list(title = "T", source_type = "manual", guids = character(0))
  staged <- stage_bundle("dashboard_template", cfg)
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)
  on.exit(unlink(config_root, recursive = TRUE), add = TRUE)

  expect_true(file.exists(file.path(staged, "connect_api.R")))
})
