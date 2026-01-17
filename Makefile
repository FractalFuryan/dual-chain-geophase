.PHONY: boundary check-boundaries

boundary: check-boundaries

check-boundaries:
	@python tools/check_boundaries.py

.PHONY: all test check
all: check-boundaries
