#!/usr/bin/env python3
"""Set up and open the demo without activating an environment by hand."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def environment_path(root, platform, version=None):
    # Windows and WSL may open the same checkout; their environments cannot mix.
    version = version or sys.version_info[:2]
    if platform == "win32":
        # NumPy DLL filenames can exceed Windows' limit inside a long repo path.
        # Keep per-checkout setup in a short user cache; no admin settings needed.
        base = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
        checkout = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:10]
        return base / "QNNDemo" / checkout / f"py{version[0]}{version[1]}"
    return root / ".demo-venv" / f"{platform}-py{version[0]}{version[1]}"


def environment_python(directory, platform):
    return directory / ("Scripts/python.exe" if platform == "win32" else "bin/python")


def numpy_version(version):
    return "1.26.4" if version < (3, 13) else "2.4.6"


def prepare(root=ROOT):
    if not (3, 10) <= sys.version_info[:2] <= (3, 14):
        raise RuntimeError(
            "Use Python 3.10 through 3.14 (3.12 is the reference version). "
            "Install it from https://www.python.org/downloads/ and run the launcher again."
        )
    directory = environment_path(root, sys.platform)
    python = environment_python(directory, sys.platform)
    if not python.exists():
        print("First run: creating the demo's own Python environment...", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(directory)
        except (OSError, subprocess.CalledProcessError) as error:
            raise RuntimeError(
                "Could not create the demo environment. On Debian/Ubuntu, install "
                "python3-venv first. On Windows/macOS, use a complete Python install "
                "from python.org. Then run this launcher again. " + str(error)
            ) from error
    expected = numpy_version(sys.version_info[:2])
    probe = subprocess.run(
        [str(python), "-c", f"import numpy; assert numpy.__version__ == {expected!r}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode:
        print(
            "Setting up NumPy. This step needs internet the first time...", flush=True
        )
        result = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "-r",
                str(root / "demo" / "requirements.txt"),
            ],
            cwd=root,
        )
        if result.returncode:
            raise RuntimeError(
                "Setup did not finish. Check your internet connection, then run the "
                "launcher again. No training or dataset download is needed. "
                "See demo/README.md for setup help."
            )
    return python


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the local URL without opening a browser.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port number; 0 chooses an available port (default).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Set up and run the demo's checks without opening a browser.",
    )
    args = parser.parse_args()
    if not 0 <= args.port < 65536:
        parser.error("Port must be between 0 and 65535.")
    try:
        python = prepare()
        command = (
            [str(python), "-m", "unittest", "discover", "-s", "demo/tests", "-v"]
            if args.check
            else [str(python), "-m", "demo", "--port", str(args.port)]
        )
        if not args.check and not args.no_browser:
            command.append("--open")
        # Keep the environment isolated from any shell-specific module settings.
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        return subprocess.call(command, cwd=ROOT, env=environment)
    except (RuntimeError, OSError) as error:
        print(f"\n{error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
