"""Launch with python -m demo --open; Ctrl+C stops the local server."""

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse
import shutil
import subprocess
import threading
import webbrowser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--open", action="store_true", help="Open the demo in your browser."
    )
    args = parser.parse_args()
    if not 0 <= args.port < 65536:
        parser.error("Port must be between 0 and 65535 (0 chooses an available port).")
    try:
        from .server import make_server

        server = make_server(args.port)
    except ModuleNotFoundError as error:
        if error.name != "numpy":
            raise
        parser.exit(
            2,
            "Install the demo dependency first: python -m pip install -r demo/requirements.txt\n",
        )
    except OSError as error:
        parser.exit(2, f"Could not start the demo: {error}. Try --port 8001.\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(
        f"\nQNN visual walkthrough: {url}\nRuns locally with bundled examples. Press Ctrl+C to stop.\n",
        flush=True,
    )
    if args.open:

        def launch():
            if os.environ.get("WSL_DISTRO_NAME") and shutil.which("cmd.exe"):
                subprocess.run(
                    ["cmd.exe", "/c", "start", "", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                webbrowser.open(url)

        threading.Timer(0.3, launch).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
