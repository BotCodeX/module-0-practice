# Defect Note: Stale Request Defect

## Impact

During the Lab 10 fault-injection exercise, a stale update was accepted and could overwrite a newer change. No production impact was observed during this exercise.

## Detection

The test function `test_conditional_update_rejects_stale_clients` failed because the stale request returned HTTP 200 instead of the expected HTTP 412.

## Timeline

1. Ran the focused test successfully before injecting the fault.
2. Temporarily removed the code that compares the stored work-item version with the client's expected version.
3. Reran the test. It failed because the stale request returned HTTP 200 instead of HTTP 412.
4. Restored the work-item version comparison.
5. Reran the focused test successfully.
6. Ran the complete test suite. All 33 tests passed.

## Root Cause

The update operation must compare the current stored work-item version with the client's expected version before applying an update. Removing this check allowed a stale request to overwrite a newer version.

## Contributing Conditions

The update operation relies on the version comparison to prevent stale updates from overwriting newer data. Without this check, outdated requests can be accepted.

## Corrective Change

Restored the original version comparison in `src/platform_api/repository.py` after temporarily removing it for fault injection.

## Verification

With the version comparison removed, the focused test failed because the stale request returned HTTP 200 instead of HTTP 412. After restoring the comparison, the focused test passed. The complete test suite also passed, with all 33 tests successful.

## Prevention

Keep the version comparison in place before saving an update, and retain the stale-update regression test to detect this type of defect.