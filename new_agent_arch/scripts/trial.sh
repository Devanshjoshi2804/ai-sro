#!/usr/bin/env bash
# One day of the trial: mine what has arrived, then write down what both
# pipelines think. Idempotent, safe to run twice, safe to skip a day.
#
#   scripts/trial.sh            once, now
#   scripts/trial.sh --serve    start the rig too, if it is not up
#
# Reading happens continuously as the extension mirrors uploads; this is only
# the daily pass and the daily record. Everything it writes goes under
# trial/YYYY-MM-DD.txt so a week is seven files to read side by side.
set -uo pipefail
cd "$(dirname "$0")/.."

DAY=$(date +%F)
OUT=trial
mkdir -p "$OUT"
LOG="$OUT/$DAY.txt"

token() { python3 -c "
import pathlib,sys
for line in pathlib.Path('.env').read_text().splitlines():
    if line.startswith(sys.argv[1] + '='): print(line.split('=',1)[1].strip()); break
" "$1"; }

if [ "${1:-}" = "--serve" ] && ! curl -s -m 2 -o /dev/null http://127.0.0.1:8100/; then
  echo "starting the rig on :8100"
  nohup uv run uvicorn rig.api:app --port 8100 --host 127.0.0.1 >> "$OUT/rig.log" 2>&1 &
  sleep 5
fi

if ! curl -s -m 3 -o /dev/null http://127.0.0.1:8100/; then
  echo "$(date -Iseconds)  rig is not answering on :8100 -- nothing mined today" | tee -a "$LOG"
  exit 1
fi

{
  echo "==================== $DAY ===================="
  date -Iseconds
  echo
  # The mining pass. One model call, billed. A day that has not grown since
  # yesterday still gets one: the pool rotates, so a second pass over the same
  # evidence sees a different window and is not a wasted call.
  echo "--- mine ---"
  curl -s -m 900 -X POST -H "Authorization: Bearer $(token RIG_INGEST_TOKEN)" \
    http://127.0.0.1:8100/v1/mine \
    | python3 -c "
import json,sys
try: r = json.load(sys.stdin)
except Exception as problem: print(f'  no answer: {problem}'); raise SystemExit
print(f\"  proposed {r.get('proposed')}  kept {r.get('kept')}  rejected {len(r.get('rejections',[]))}\")
c = r.get('coverage') or {}
print(f\"  coverage {c.get('coverage')}  skew {c.get('skew')}  lopsided {r.get('lopsided')}\")
print(f\"  left_out {len(r.get('left_out',[]))}  pool lost {len(r.get('lost_pool',[]))}\")
for x in r.get('rejections', []): print(f\"  refused {x.get('workflow_title')!r}: {x.get('reason')}\")
if r.get('error'): print(f\"  the model refused this pass: {r['error']}\")
"
  echo
  echo "--- both pipelines ---"
  SRO_TOKEN=$(token SRO_TOKEN) uv run python scripts/compare.py --tenant "$(token RIG_TENANT)" 2>&1 \
    | grep -v "^Direct use"
  echo
  echo "--- what the pool is holding ---"
  curl -s -m 30 -H "Authorization: Bearer $(token RIG_INGEST_TOKEN)" \
    "http://127.0.0.1:8100/v1/pool" \
    | python3 -c "
import json,sys
try: r = json.load(sys.stdin)
except Exception: print('  unavailable'); raise SystemExit
print(f\"  live {r.get('live')}  retired {r.get('retired')}\")
for entry in (r.get('entries') or [])[:5]:
    print(f\"    {entry.get('gesture_id')} retired: {entry.get('reason')}\")
"
} >> "$LOG" 2>&1

echo "wrote $LOG"
tail -n 24 "$LOG"
