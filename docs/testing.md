# Testing

This guide covers how WSD is tested: how to run the tests, what each test covers, how the Linux backend is tested without real hardware, and how to maintain the tests.

## 1. Setup

You need:

- **Python 3.10 or newer**
- **Node.js 22** (for the frontend tests)
- The Python test dependencies:

```bash
python -m pip install pytest flask "scikit-learn>=1.5,<2"
```

On Windows, the Windows collector tests also need:

```bash
python -m pip install WMI pywin32 pywintrace psutil
```

All commands below are run from the repository root.

---

## 2. Running the tests locally

| What | Command |
|---|---|
| All backend tests (CORE, HTTP API, database, Linux backend, integration) | `python -B -m pytest tests -q` |
| ALGO-01 unit tests (without the slow ML benchmarks) | `python -B -m pytest backend/algorithms/algo01/tests -q -m "not benchmark"` |
| ALGO-01 ML benchmarks only | `python -B -m pytest backend/algorithms/algo01/tests -q -m benchmark` |
| ALGO-02 unit tests | `python -B -m pytest backend/algorithms/algo02/tests -q` |
| Windows launcher tests | `python -B -m pytest packaging/windows/tests -q` |
| Frontend tests | `npm test` (runs `node --test` on `tests/*.test.js`) |
| Lint (same rules as CI) | `ruff check . --select E9,F63,F7,F82` |

A normal run of `pytest tests` ends with **passed**, **skipped** and **xfailed** results and no failures. Skipped and xfailed tests are expected; see [section 5](#5-maintenance).

---

## 3. What the tests cover

| Area | Where | How it is tested |
|---|---|---|
| HTTP API contract | `tests/contract/test_http_contract.py` | Every endpoint returns the documented `{status, data, error}` envelope and fields ([API contracts](api-contracts.md)). |
| Algorithm contract | `tests/contract/test_algorithm_contract.py` | ALGO-01 and ALGO-02 return recommendations in the shared format. |
| End to end | `tests/integration/test_e2e_demo.py` | Starts the whole app in demo mode and calls it like the frontend does. |
| Process history (US-02) | `tests/integration/test_us02_history.py`, `tests/test_us02_identity.py` | History is stored and processes are identified by PID **and** start time. |
| Database | `tests/test_db_contract.py`, `tests/test_db_file_io.py` | Real SQLite database in a temporary folder: metrics, file activity, file subscriptions and file move records, including data surviving a restart. |
| CORE ↔ Linux backend | `tests/test_linux_core_adapter.py` | A **fake Linux backend** returns normal results or any backend error code on demand. Checks that errors are caught and returned as JSON errors, and that file activity has exactly the contract fields, in UTC. |
| CORE file subscriptions and moves | `tests/test_core_file_subscriptions.py` | Track/untrack files and folders, start a move and read its progress, saving file activity every minute, and the `ssd_caching` mode switch. |
| Linux backend | `tests/linux/` | Drive detection with fake `lsblk` output, process and disk stats from the runner's real `/proc`, and file tracking with a stand-in for BCC. |
| Frontend | `tests/*.test.js` | API client, formatting, process rendering, mock data and the File I/O page. |
| Algorithms | `backend/algorithms/algo01/tests`, `backend/algorithms/algo02/tests` | Unit tests for each policy. |

### Why the Linux backend uses fakes

The Linux backend traces file reads and writes with **eBPF through BCC**. That needs root, a real kernel and real disks, which CI runners do not have. So testing is split in two:

- **In CI (every PR):** `tests/linux/conftest.py` loads a small stand-in `bcc` module when BCC is not installed, so the tracking logic can be tested without the kernel. On Windows, the Linux tests skip themselves.
- **On a real Linux machine (manual):** the real-machine script below.

### Real-machine script (Linux only)

```bash
sudo bash scripts/linux_local_test.sh            # default port 5055
sudo bash scripts/linux_local_test.sh --port 6000
sudo bash scripts/linux_local_test.sh --skip-server
```

It runs four steps and prints a PASS / FAIL / SKIP summary:

1. **Requirements:** Linux, root, Python 3.10+, flask, pytest, BCC (`python3-bcc` on Fedora, `python3-bpfcc` on Ubuntu), `lsblk` and `curl`.
2. **Unit tests:** runs `tests/linux` with pytest.
3. **Real BCC file monitoring:** tracks a real file and checks reads and writes are seen.
4. **WSD in real mode:** starts WSD without `--demo`, writes about 2 GB with `dd` to create disk activity, and checks `/api/v1/devices`, `/api/v1/metrics/latest` and `/api/v1/processes/latest` report real values (including the `dd` process). `--skip-server` skips this step.

This script does **not** test mergerfs pooling or file moves; those are tested by hand on the Linux test machine.

---

## 4. Tests in CI

Every pull request runs the tests automatically on GitHub Actions ([`.github/workflows/tests.yml`](../.github/workflows/tests.yml)):

| Job | Runs on | Tests |
|---|---|---|
| `algo01-unit-tests` | Ubuntu and Windows, Python 3.10 and 3.12 | ALGO-01 (without benchmarks), ALGO-02, all of `tests/` and the Windows launcher tests |
| `frontend-tests` | Ubuntu, Node 22 | `npm test` |
| `lint` | Ubuntu | `ruff check . --select E9,F63,F7,F82` |

A pull request cannot be merged until all of these pass. On Windows, the Linux backend tests in `tests/linux/` skip themselves.

---

## 5. Maintenance

- **Tests that skip themselves until code is merged.** Some test files test code that lives on another branch. They check for that code first and skip if it is not on `main` yet, so CI stays green. They turn on automatically when the branch merges.
- **`xfail(strict=True)` marks known bugs.** These tests describe what the API contract asks for but the code does not do yet (for example, some invalid requests return 500 instead of 4xx). They show as **xfailed** and do not fail CI. When the bug is fixed, the test **XPASSes** and fails the run on purpose: remove the `xfail` marker so it becomes a normal test.
- **ML benchmarks are not run in CI.** They are marked `benchmark` (see `pytest.ini`) and excluded with `-m "not benchmark"`.
- **After `main` changes, close and reopen a PR to re-test it.** A PR's checks test the PR merged with `main`. **Re-run jobs** can repeat the old merge preview, so it may fail even after the fix is on `main`. Closing and reopening the PR, or pushing a new commit, creates a fresh run.
- **Tests must not depend on the real clock.** Pass fixed times into code under test. A test that compares a fixed timestamp to the current time will pass for a few minutes and then fail on every PR.
- **Keep fakes in line with the real backend.** The fake Linux backend uses the real `ErrorCode` values and data models from `backend/linux`. If a backend function changes what it returns, update the fake in the same PR.
- **When adding a test file for Linux-only code**, put it in `tests/linux/` so it skips on Windows.

---

## 6. Non-functional requirements (testing)

| Requirement | How it is met |
|---|---|
| **Reliability:** broken code must not reach `main` | Every PR runs the full test suite and lint, and cannot merge until they pass. |
| **Portability:** WSD must work on the platforms we support | Backend tests run on Windows and Ubuntu with Python 3.10 and 3.12. |
| **Maintainability:** tests must run anywhere, without special hardware | Fakes replace the kernel tracer and disk listings, so the tests need no root, BCC or extra disks. Linux-only tests skip on Windows. |
| **Testability of real hardware** | One `sudo` script checks BCC, real disks and WSD in real mode on an actual Linux machine. |
| **Fast feedback** | Slow ML benchmarks are excluded from CI, and a newer push to a PR cancels the older run. |
| **Contract correctness** | Contract tests check every HTTP endpoint and both algorithms against the documented formats in [API contracts](api-contracts.md). |

---

## 7. Known limitations

- The real-machine script is **manual**: a regression in the kernel-tracing code only shows up when someone runs it.
- CI does not run eBPF, mergerfs or real file moves.
- Line coverage is not measured yet.
- Some invalid requests to the file subscription and move endpoints still return HTTP 500 instead of a 4xx error. Each one has an `xfail` test in `tests/test_core_file_subscriptions.py`.
