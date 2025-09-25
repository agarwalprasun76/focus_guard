
# TESTING PROMPT (pytest, simple & focused)

## Goal: Write a small number of high-quality unit tests for the function(s) in this file/module.

## Constraints & Organization

Use pytest.

Add tests under the existing tests/ folder.

Unit tests → tests/unit/; Integration tests → tests/integration/.

Keep tests isolated (no external network/FS unless explicitly required; then mark as integration).

## Write tests that include

Clear test names describing behavior + condition.

Correctness assertions for outputs and side effects.

Edge cases & boundary values (e.g., 0, 1, empty, None, max/min, empty collections).

Failures & exceptions (type/value errors where applicable).

Parametrization for repetitive logic.

Fixtures only if setup/teardown is truly shared (keep simple).

## Improve or extend existing tests by

Adding missing edge cases / uncovered branches.

Making names more descriptive.

Eliminating redundant tests.

Using @pytest.mark.parametrize for repeated scenarios.

Asserting both result and invariants (e.g., lengths, ordering, idempotence).

## Analysis requirements

Identify uncovered branches/conditions (e.g., early returns, error paths, boolean flags).

Cover exception-raising scenarios.

Consider unexpected types/structures if function isn’t type-strict.

## Quality & Coverage

Prefer 3–6 great tests over many weak ones.

Run: pytest -q --maxfail=1 while iterating; then
pytest --cov=<package> --cov-report=term-missing.

Report what branches remain untested (if any) and why.

## Deliverables 

The test code (pytest).

A short rationale list (1–2 sentences per test) explaining why each test exists.

A brief coverage/branch-gaps note.


