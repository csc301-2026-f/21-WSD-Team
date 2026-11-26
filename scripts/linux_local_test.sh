#!/usr/bin/env bash
set -u

PY="${PYTHON:-python3}"
PORT=5055
SKIP_SERVER=0

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --skip-server) SKIP_SERVER=1; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

PASS=0; FAIL=0; SKIP=0
pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
skip() { echo "  [SKIP] $1"; SKIP=$((SKIP + 1)); }
section() { echo; echo "== $1"; }

WORK="$(mktemp -d /var/tmp/wsd-local-test.XXXXXX)"
SERVER_PID=""

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null
  rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# --------------------------------------------------------------------------- #
section "1. Requirements"
# --------------------------------------------------------------------------- #
[ "$(uname -s)" = "Linux" ] && pass "running on Linux ($(uname -r))" || { fail "not Linux"; exit 1; }
[ "$(id -u)" = 0 ] && pass "running as root" || fail "not root: run with sudo (BCC needs it)"

if "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  pass "$("$PY" --version 2>&1)"
else
  fail "Python 3.10+ not found ($PY)"; exit 1
fi

"$PY" -c 'import flask' 2>/dev/null && pass "flask installed" \
  || fail "flask missing for $PY (pip install flask, or dnf install python3-flask)"
"$PY" -c 'import pytest' 2>/dev/null && HAVE_PYTEST=1 || HAVE_PYTEST=0
[ "$HAVE_PYTEST" = 1 ] && pass "pytest installed" || skip "pytest missing (pip install pytest): step 2 skipped"

if "$PY" -c 'import bcc' 2>/dev/null; then HAVE_BCC=1; pass "bcc installed"
else HAVE_BCC=0; fail "bcc missing for $PY (Fedora: dnf install python3-bcc, Ubuntu: apt install python3-bpfcc)"; fi

command -v lsblk >/dev/null && pass "lsblk found" || fail "lsblk missing (util-linux)"
command -v curl >/dev/null && HAVE_CURL=1 || HAVE_CURL=0
[ "$HAVE_CURL" = 1 ] && pass "curl found" || fail "curl missing: step 5 needs it"


# --------------------------------------------------------------------------- #
section "2. Unit tests (tests/linux)"
# --------------------------------------------------------------------------- #
if [ "$HAVE_PYTEST" = 1 ]; then
  if "$PY" -m pytest tests/linux -q -p no:cacheprovider; then
    pass "tests/linux"
  else
    fail "tests/linux (see output above)"
  fi
else
  skip "pytest not installed"
fi

# --------------------------------------------------------------------------- #
section "3. Real BCC/eBPF file monitoring"
# --------------------------------------------------------------------------- #
if [ "$HAVE_BCC" = 1 ] && [ "$(id -u)" = 0 ]; then
  "$PY" - "$WORK" <<'PYEOF'
import os, sys, time

work = sys.argv[1]
from backend.linux.collector import FileIOCollector
from backend.linux.models import ErrorCode, FileMetric

path = os.path.join(work, "bcc-test.bin")
with open(path, "wb") as f:
    f.write(os.urandom(1 << 20))

collector = FileIOCollector()
file = collector.track(path)          # tracked before start, so the first sample has it
if isinstance(file, ErrorCode):
    print(f"  [FAIL] track() returned {file!r}"); sys.exit(1)

started = collector.start()
if started == ErrorCode.FILE_TRACER_UNAVAILABLE:
    print(f"  [FAIL] eBPF tracer unavailable: {collector.last_error!r}")
    print("         (needs kernel BTF + fentry support; check: ls /sys/kernel/btf/vmlinux)")
    sys.exit(1)

try:
    time.sleep(0.2)
    with open(path, "rb") as f:
        for _ in range(8):
            f.seek(0); f.read(64 * 1024)
    with open(path, "r+b") as f:
        for _ in range(4):
            f.write(b"z" * 4096)
    time.sleep(2.5)
    metric = collector.get_metrics(2).get(file)
finally:
    collector.stop()

ok = isinstance(metric, FileMetric) and metric.read_attempts > 0 and metric.write_attempts > 0
print(("  [PASS] " if ok else "  [FAIL] ") +
      (f"reads/writes counted: read_attempts={metric.read_attempts}, "
       f"write_attempts={metric.write_attempts}" if isinstance(metric, FileMetric)
       else f"no metric for the tracked file ({metric!r})"))
sys.exit(0 if ok else 1)
PYEOF
  [ $? = 0 ] && pass "BCC file monitoring" || fail "BCC file monitoring (see above)"
else
  skip "needs bcc and root"
fi

# --------------------------------------------------------------------------- #
section "4. WSD in real mode (no --demo)"
# --------------------------------------------------------------------------- #
api_check() {  # api_check <path> <python condition on `data`> <label>
  local body
  body="$(curl -s --max-time 5 "http://127.0.0.1:$PORT$1")" || return 1
  printf '%s' "$body" | "$PY" -c "
import json, sys
r = json.load(sys.stdin)
data = r.get('data')
sys.exit(0 if r.get('status') == 'success' and ($2) else 1)
" 2>/dev/null
}

if [ "$SKIP_SERVER" = 1 ]; then
  skip "--skip-server given"
elif [ "$HAVE_CURL" = 0 ]; then
  skip "curl missing"
else
  "$PY" -m backend.main --port "$PORT" --data-dir "$WORK/data" >"$WORK/server.log" 2>&1 &
  SERVER_PID=$!
  up=0
  for _ in $(seq 1 30); do
    curl -s --max-time 1 "http://127.0.0.1:$PORT/api/v1/devices" >/dev/null 2>&1 && { up=1; break; }
    kill -0 "$SERVER_PID" 2>/dev/null || break
    sleep 1
  done

  if [ "$up" = 0 ]; then
    fail "WSD did not start; last log lines:"; tail -n 15 "$WORK/server.log" | sed 's/^/         /'
  else
    pass "WSD started in real mode on port $PORT"
    api_check /api/v1/devices "isinstance(data, list) and len(data) >= 1" \
      && pass "/api/v1/devices lists at least one real drive" \
      || fail "/api/v1/devices returned no drives or an error"

    # Generate real disk writes while polling the API
    dd if=/dev/zero of="$WORK/io.bin" bs=1M count=2048 oflag=direct status=none 2>/dev/null &
    DD_PID=$!
    disk_ok=0; proc_ok=0
    for _ in $(seq 1 10); do
      sleep 1
      api_check /api/v1/metrics/latest \
        "any((m.get('write_bytes_per_sec') or 0) > 0 for m in data)" && disk_ok=1
      api_check /api/v1/processes/latest \
        "any(p.get('process_name') == 'dd' and (p.get('write_bytes_per_sec') or 0) > 0 for p in data)" \
        && proc_ok=1
      [ "$disk_ok" = 1 ] && [ "$proc_ok" = 1 ] && break
      kill -0 "$DD_PID" 2>/dev/null || break
    done
    kill "$DD_PID" 2>/dev/null; wait "$DD_PID" 2>/dev/null

    [ "$disk_ok" = 1 ] && pass "/api/v1/metrics/latest shows disk writes" \
      || fail "/api/v1/metrics/latest never showed disk writes"
    [ "$proc_ok" = 1 ] && pass "/api/v1/processes/latest shows the dd process writing" \
      || fail "/api/v1/processes/latest never showed dd writing"
    if [ "$disk_ok" = 0 ] || [ "$proc_ok" = 0 ]; then
      echo "         Server log (last lines):"; tail -n 10 "$WORK/server.log" | sed 's/^/         /'
    fi
  fi
fi

# --------------------------------------------------------------------------- #
echo
echo "== Summary: $PASS passed, $FAIL failed, $SKIP skipped"
[ "$FAIL" = 0 ]
