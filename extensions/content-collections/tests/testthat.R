library(testthat)

# Source helpers under test
helpers <- list.files("../R", pattern = "\\.R$", full.names = TRUE)
for (f in helpers) source(f, local = FALSE)

test_dir(".")
