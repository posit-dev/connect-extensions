
test_that("filter_visits_by_time_window works with different session window settings", {
  # Sample data with timestamps 30 seconds and 5 minutes apart
  visits <- data.frame(
    content_guid = rep("guid1", 3),
    user_guid = rep("user1", 3),
    timestamp = as.POSIXct(c(
      "2023-01-01 10:00:00",
      "2023-01-01 10:00:30",
      "2023-01-01 10:05:00"
    ))
  )

  # With session_window = 0, all visits should remain
  result0 <- filter_visits_by_time_window(visits, 0)
  expect_equal(nrow(result0), 3)

  # With session_window = 60, the second visit should be filtered out
  result60 <- filter_visits_by_time_window(visits, 60)
  expect_equal(nrow(result60), 2)
  expect_equal(
    as.character(result60$timestamp),
    c("2023-01-01 10:00:00", "2023-01-01 10:05:00")
  )
})

test_that("filter_visits_by_time_window handles multiple users separately", {
  # Sample with two users
  visits <- data.frame(
    content_guid = "guid1",
    user_guid = c("user1", "user1", "user2", "user2"),
    timestamp = as.POSIXct(c(
      "2023-01-01 10:00:00",
      "2023-01-01 10:00:30",
      "2023-01-01 10:00:00",
      "2023-01-01 10:00:30"
    ))
  )

  result <- filter_visits_by_time_window(visits, 60)
  expect_equal(nrow(result), 2) # One visit per user remains
  expect_equal(sort(unique(result$user_guid)), c("user1", "user2"))
})
