"""Hidden, detached service launcher for AI Video Assets.

Runs uvicorn in a child process completely detached from the launching shell
(WorkBuddy, explorer, or Task Scheduler), with output redirected to service.log.
No console window is created when launched via pythonw.exe.
"""
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
LOG = os.path.join(ROOT, "service.log")
PORT = 8000
HEALTH = f"http://127.0.0.1:{PORT}/api/health"

# Windows process creation flags: no console window + new process group + detached
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
FLAGS = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def log(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def find_python() -> str:
    config = os.path.join(ROOT, "service-config.bat")
    if os.path.isfile(config):
        for line in open(config, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line.startswith("set \"PY=") and line.endswith("\""):
                candidate = line[len('set "PY='):-1]
                if os.path.isfile(candidate):
                    return candidate
    if os.path.isfile(sys.executable):
        return sys.executable
    return "python"


def is_running() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> None:
    if is_running():
        log("Service already running, skip duplicate start")
        return

    python = find_python()
    log(f"Starting detached service with {python}")
    with open(LOG, "a", encoding="utf-8") as output:
        output.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] === service start ===\n")
        output.flush()
        subprocess.Popen(
            [python, "-m", "uvicorn", "serve:app", "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=BACKEND,
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=FLAGS,
            close_fds=True,
        )

    for _ in range(40):
        if is_running():
            log("Service is up")
            return
        time.sleep(0.5)
    log("WARNING: service did not respond within 20s, check log")


if __name__ == "__main__":
    main()
