for s in charload scdata storage registry reglong; do one "load errors: $s" "$SP/run_load_errors.sh" "$RUN" "$s"; done
