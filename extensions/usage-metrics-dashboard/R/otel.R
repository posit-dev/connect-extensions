is_otel_tracing <- function() {
  requireNamespace("otel", quietly = TRUE) && otel::is_tracing_enabled()
}
