#!/usr/bin/env bash
set -euo pipefail

# Minimal end-to-end verifier for Step 2 backend
# Requires: bash, curl, python3, ffmpeg, uvicorn, sqlite3 (optional for manual inspection)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/backend"
VIDEO_PATH="${TMPDIR:-/tmp}/clipcut_sample.mp4"
PORT=8000
BASE_URL="http://127.0.0.1:${PORT}"
UVICORN_LOG="${TMPDIR:-/tmp}/clipcut_uvicorn.log"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

wait_for_health() {
  local retries=30
  until curl -sf "${BASE_URL}/health" >/dev/null 2>&1; do
    retries=$((retries-1))
    if [[ $retries -le 0 ]]; then
      echo "Server did not become healthy" >&2
      exit 1
    fi
    sleep 1
  done
}

poll_job_success() {
  local video_id=$1
  local timeout=60
  while [[ $timeout -gt 0 ]]; do
    body=$(curl -sf "${BASE_URL}/api/videos/${video_id}")
    status=$(python - <<'PY'
import json,sys
obj=json.load(sys.stdin)
jobs=obj.get("jobs",[])
status=jobs[0]["status"] if jobs else None
print(status or "")
PY
<<<"$body")
    if [[ "$status" == "SUCCESS" ]]; then
      echo "$body"
      return 0
    elif [[ "$status" == "FAILED" ]]; then
      echo "Job failed" >&2
      return 1
    fi
    sleep 2
    timeout=$((timeout-2))
  done
  echo "Timed out waiting for job" >&2
  return 1
}

parse_field() {
  local json=$1
  local field=$2
  python - <<PY
import json,sys
obj=json.loads(sys.argv[1])
val=obj.get(sys.argv[2])
print(val if val is not None else "")
PY
"$json" "$field"
}

start_server() {
  pushd "$ROOT_DIR" >/dev/null
  uvicorn app.main:app --app-dir "$APP_DIR" --port "$PORT" --log-level info >"$UVICORN_LOG" 2>&1 &
  SERVER_PID=$!
  popd >/dev/null
  wait_for_health
}

create_sample_video() {
  if [[ -f "$VIDEO_PATH" ]]; then return; fi
  ffmpeg -y -f lavfi -i color=c=blue:s=640x360:d=3 -f lavfi -i sine=frequency=440:duration=3 -shortest -c:v libx264 -c:a aac "$VIDEO_PATH" >/dev/null 2>&1
}

restart_server() {
  cleanup
  unset SERVER_PID
  start_server
}

main() {
  create_sample_video
  start_server

  # Upload video
  upload_resp=$(curl -sf -F "file=@${VIDEO_PATH}" "${BASE_URL}/api/videos")
  video_id=$(parse_field "$upload_resp" "video_id")
  job_id=$(parse_field "$upload_resp" "job_id")
  echo "Uploaded video_id=${video_id} job_id=${job_id}"

  # Wait for ingest job to succeed
  video_json=$(poll_job_success "$video_id")

  duration=$(parse_field "$video_json" "duration_seconds")
  fps=$(parse_field "$video_json" "fps")
  meta=$(parse_field "$video_json" "raw_metadata")

  if [[ -z "$duration" || -z "$fps" || -z "$meta" ]]; then
    echo "Metadata missing (duration/fps/raw_metadata)" >&2
    exit 1
  fi
  echo "Metadata persisted: duration=${duration}, fps=${fps}"

  # Restart safety check
  restart_server
  post_restart_json=$(curl -sf "${BASE_URL}/api/videos/${video_id}")
  pr_duration=$(parse_field "$post_restart_json" "duration_seconds")
  pr_fps=$(parse_field "$post_restart_json" "fps")
  pr_meta=$(parse_field "$post_restart_json" "raw_metadata")

  if [[ "$pr_duration" != "$duration" || "$pr_fps" != "$fps" || -z "$pr_meta" ]]; then
    echo "Restart safety failed: metadata mismatch or missing" >&2
    exit 1
  fi

  echo "All checks passed"
}

main "$@"
