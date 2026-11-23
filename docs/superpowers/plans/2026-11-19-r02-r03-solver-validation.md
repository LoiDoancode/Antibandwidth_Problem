# R02/R03 Solver Validation Implementation Plan

> **For agentic workers:** Use the installed executing-plans and test-driven-development skills to implement these tasks inline, followed by one independent review.

**Goal:** Fix only review items R02 and R03 authorized by the user.

**Architecture:** Reject unsupported SAT search methods at the API and CLI boundaries. Parse external SAT results explicitly and raise an error for failure, UNKNOWN, missing/contradictory status, or incompatible exit codes instead of reporting UNSAT.

**Tech Stack:** Python, pytest, NetworkX, PySAT; existing temporary test dependencies.

**Spec:** User instruction in this conversation: "Sửa mình ý 2 và ý 3 thôi nhé"; detailed reproductions R02/R03 in CODE_REVIEW_NOTES.md.

## Global Constraints

- Change production code only for R02/R03, in src/solver.py and main.py.
- Do not change graph loading, CP-SAT, optimization-status reporting, benchmark behavior, datasets, dependencies, or existing benchmark results.
- Preserve binary_search, linear_search, incremental, and CP-SAT direct_optimize.
- Accept conventional SAT/UNSAT exit codes 10/20 with matching status; also accept code 0 with an explicit valid status for wrappers.
- Do not create commits, change branches, or ask again for authorization already given for these fixes.

## Review Focus

- Invalid methods on trivial graphs must still be rejected (Task 1).
- CP-SAT selected through either --solver or --encoding must retain direct_optimize (Task 1).
- UNKNOWN, absent status, contradictory statuses and mismatching exit codes must not lower a search bound (Task 2).
- Multiline valid models and legacy exit-code-0 wrappers must keep working (Task 2).
- External failure and timeout must remove the temporary CNF and stop without printing an UNSAT result (Task 2).

## Task 1: Reject unsupported SAT search methods

Files: src/solver.py, main.py, tests/test_solver.py, tests/test_cli.py.

Interface: AntibandwidthSolver.solve(method, use_bounds) retains its result for the three supported methods; invalid methods raise ValueError. CLI rejects direct_optimize for SAT with argparse exit code 2.

- [x] Add parametrized API regression tests for direct_optimize/unknown methods, Direct/SCL and trivial/nontrivial graphs; add CLI tests rejecting SAT and retaining both CP-SAT selectors.
- [x] Run the new tests; confirm missing-validation failures.
- [x] Validate method before early returns in solve(); validate solver/method combination in parse_args().
- [x] Run the new tests and full suite; expect all passing.

## Task 2: Reject inconclusive or failed external solver results

Files: src/solver.py, main.py, tests/test_solver.py, tests/test_cli.py.

Interface: check_sat_external() keeps (bool, model-or-None, elapsed) only for a conclusive SAT/UNSAT result. Failures/UNKNOWN raise RuntimeError; subprocess timeout keeps TimeoutError. Temporary CNF cleanup is preserved.

- [x] Add tests using subprocess results at the external-process boundary: valid SAT/UNSAT, multiline model, error exit, UNKNOWN/missing/contradictory status, mismatching exit codes, malformed literals and launch errors; check cleanup and failure propagation through solve().
- [x] Run new tests; confirm external failures are currently treated as UNSAT.
- [x] Implement explicit status/exit-code validation and clear diagnostics, preserving normal results; make CLI show errors with a nonzero exit instead of an UNSAT/result summary.
- [x] Run targeted tests, full pytest suite, CI lint, git diff --check and an independent scoped review.
- [x] Update only the R02/R03 status in review notes with fresh verification results.
