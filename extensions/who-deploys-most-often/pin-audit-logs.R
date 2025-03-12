#' ---
#' title: "Script to get and pin a large segment of audit logs data"
#' ---

library(connectapi)
library(pins)

client <- connect()

audit_logs <- get_audit_logs(client, limit = 1000000, asc_order = FALSE)

board <- board_connect()
PIN_NAME <- paste0(board$account, "/", "connect_metrics_cache_audit_logs")

pin_write(board, audit_logs, name = PIN_NAME)

# To read the data, run: `pin_read(board, PIN_NAME)`
