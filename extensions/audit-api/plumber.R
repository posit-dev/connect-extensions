library(plumber)
library(dplyr)
library(connectapi)

client <- connect()

get_hours_of_audit_logs <- function(cnct, hours = 1, max_retries = 3) {
    end_time <- Sys.time()
    target_time <- end_time - as.difftime(hours, units = "hours")

    fetch_audit_logs <- function(current_logs = NULL, retry_count = 0) {
        new_logs <- get_audit_logs(cnct, asc_order = FALSE)

        if(nrow(new_logs) == 0 && retry_count < max_retries) {
            return(fetch_logs(current_logs, retry_count + 1))
        }

        if (nrow(new_logs) == 0) {
            return(current_logs)
        }

        combined_logs <- if (!is.null(current_logs)) {
            bind_rows(current_logs, new_logs)
        } else {
            new_logs
        }

        oldest <- combined_logs |>
            slice_min(order_by = time, with_ties = FALSE, na_rm = TRUE) |>
            pull(time)

        if (oldest <= target_time) {
            return(combined_logs |> filter(time >= target_time))
        } else {
            return(fetch_audit_logs(combined_logs))
        }
    }

    fetch_audit_logs() |>
        arrange(desc(time))
}

filter_audit_logs <- function(audit_logs, event) {
  audit_logs |>
    filter(action == event)
}

#* @apiTitle filtered audit logs
#* @apiDescription provide an endpoint publishers can call to retrieve audit logs for audited events. See https://docs.posit.co/connect/admin/auditing/ for the list of audited events.


#* get filtered logs
#* @get /logs
#* @param interval:int how many hours of logs you want
#* @param audited_event:str audited event
get_filtered_logs <- function(interval, audited_event) {
  interval <- as.integer(interval)
  get_hours_of_audit_logs(client, interval) |>
    filter_audit_logs(audited_event)
}
