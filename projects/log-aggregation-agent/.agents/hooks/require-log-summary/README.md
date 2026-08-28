# Log summary finish gate

The hook reruns the deterministic aggregation and validates that the generated
manifest covers every input line. It fails closed when reports are missing,
line ranges are invalid, or the summary is inconsistent with the source log.
