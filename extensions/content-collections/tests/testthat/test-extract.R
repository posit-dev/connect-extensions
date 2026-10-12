test_that("extract_collection_json returns parsed config when present", {
  json <- '{"title":"X","theme":"warm","source_type":"manual","guids":["g1"]}'
  tarball <- make_bundle_tarball(list("collection.json" = json))

  cfg <- extract_collection_json(tarball)
  expect_equal(cfg$title, "X")
  expect_equal(cfg$theme, "warm")
  expect_equal(cfg$guids, list("g1"))
})

test_that("extract_collection_json returns NULL when missing", {
  tarball <- make_bundle_tarball(list("index.qmd" = "---\ntitle: x\n---"))
  expect_null(extract_collection_json(tarball))
})

test_that("extract_collection_json returns NULL on unreadable tarball", {
  not_a_tar <- tempfile(); writeLines("garbage", not_a_tar)
  expect_null(extract_collection_json(not_a_tar))
})
