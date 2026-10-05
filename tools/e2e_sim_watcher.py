"""Run `simctl` on the host for `SimulatorScreenDriveTests`, which cannot.

    python3 tools/e2e_sim_watcher.py <simulator-udid> <command-dir> <screenshot-dir>

The test writes `<id>.cmd` (JSON) into the command directory and waits for
`<id>.done`. Three commands:

  * `shot`  — `simctl io <udid> screenshot <screenshot-dir>/<label>.png`
  * `set`   — `simctl location <udid> set lat,lon`
  * `play`  — `simctl location <udid> start --speed=<m/s> --interval=1 -`,
              waypoints on stdin (a long route overflows argv otherwise, and
              one malformed pair rejects the whole list)

Pass the test the same command directory as `SUNDAYDRIVE_E2E_SCREENS`
(`TEST_RUNNER_SUNDAYDRIVE_E2E_SCREENS=...` through xcodebuild). Stop with
Ctrl-C. The harness brief has the
environment gotchas: git show a2ddddc:docs/overnight-e2e-drives-brief.md.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def run(udid, cmd, shots):
    kind = cmd["cmd"]
    if kind == "shot":
        out = shots / f"{cmd['label']}.png"
        r = subprocess.run(["xcrun", "simctl", "io", udid, "screenshot", str(out)],
                           capture_output=True, text=True)
        return f"{r.returncode} {out}"
    if kind == "set":
        lat, lon = cmd["point"]
        r = subprocess.run(["xcrun", "simctl", "location", udid, "set", f"{lat:.7f},{lon:.7f}"],
                           capture_output=True, text=True)
        return f"{r.returncode} {r.stderr.strip()}"
    if kind == "play":
        points = "".join(f"{lat:.7f},{lon:.7f}\n" for lat, lon in cmd["points"])
        r = subprocess.run(["xcrun", "simctl", "location", udid, "start",
                            f"--speed={cmd['speed']}", "--interval=1", "-"],
                           input=points, capture_output=True, text=True)
        return f"{r.returncode} {len(cmd['points'])} points {r.stderr.strip()}"
    return f"unknown command {kind}"


def main(argv):
    udid, cmds, shots = argv[1], Path(argv[2]), Path(argv[3])
    cmds.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    print(f"watching {cmds} for {udid}", flush=True)
    while True:
        for path in sorted(cmds.glob("*.cmd")):
            cmd = json.loads(path.read_text())
            reply = run(udid, cmd, shots)
            print(time.strftime("%H:%M:%S"), cmd["id"], cmd["cmd"], cmd.get("label", ""), reply,
                  flush=True)
            path.with_suffix(".done").write_text(reply)
            path.unlink()
        time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
