"""Start a deterministic analysis demo with real SQL execution in one terminal."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def wait_for_api(url: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The API stopped during startup; check its output above.")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("The API did not become ready within 30 seconds.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3000)
    args = parser.parse_args()
    npm = shutil.which("npm")
    if not npm or not (ROOT / "apps/web/node_modules/next").is_dir():
        print("Install Node.js and run npm ci --prefix apps/web first.", file=sys.stderr)
        return 1
    if args.api_port == args.web_port:
        print("Choose different API and frontend ports.", file=sys.stderr)
        return 1
    for port in (args.api_port, args.web_port):
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("127.0.0.1", port))
        except OSError:
            print(f"Port {port} is already in use. Stop the earlier server with Ctrl+C, then retry. "
                  f"If GapMap is already running, open http://localhost:{args.web_port}.", file=sys.stderr)
            return 1

    env = {
        **os.environ,
        "GAPMAP_DEMO_MODE": "1",
        "GAPMAP_LLM_PROVIDER": "demo",
        "NEXT_PUBLIC_GAPMAP_MOCK": "false",
        "GAPMAP_API_URL": f"http://127.0.0.1:{args.api_port}",
        "NEXT_TELEMETRY_DISABLED": "1",
        "PYTHONUNBUFFERED": "1",
    }
    processes: list[subprocess.Popen] = []

    def stop(_signal, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gapmap.apps.api.main:app", "--host", "127.0.0.1", "--port", str(args.api_port)],
            cwd=ROOT, env=env, start_new_session=True,
        )
        processes.append(api)
        wait_for_api(f"http://127.0.0.1:{args.api_port}/api/health", api)
        processes.append(subprocess.Popen(
            [npm, "run", "dev", "--prefix", "apps/web", "--", "--hostname", "127.0.0.1", "--port", str(args.web_port)],
            cwd=ROOT, env=env, start_new_session=True,
        ))
        print(f"\nGapMap demo: http://localhost:{args.web_port}", flush=True)
        print("Bundled analysis + real SQL grading. No AI key or external AI request.\nCtrl+C stops both servers.\n", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.3)
        raise RuntimeError("A server stopped. Read its output above, then run npm run demo again.")
    except KeyboardInterrupt:
        print("\nStopping GapMap…", flush=True)
        return 0
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        # npm can forward Ctrl+C after the terminal has already delivered it.
        # Finish child cleanup even when that second signal arrives.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        for process in reversed(processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
