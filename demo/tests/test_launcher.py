"""Check setup isolation, offline restarts, and paths containing spaces."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "demo_launcher", ROOT / "ONE-CLICK-LAUNCHERS" / "launch_demo.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_environment_paths_separate_systems_and_python_versions(self):
        root = Path("project with spaces").resolve()
        linux = launcher.environment_path(root, "linux", (3, 12))
        self.assertNotEqual(linux, launcher.environment_path(root, "darwin", (3, 12)))
        self.assertNotEqual(linux, launcher.environment_path(root, "linux", (3, 13)))
        with patch.dict(launcher.os.environ, {"LOCALAPPDATA": str(root / "cache")}):
            windows = launcher.environment_path(root, "win32", (3, 12))
            self.assertIn("QNNDemo", windows.parts)
            self.assertNotIn(".demo-venv", windows.parts)
        self.assertEqual(
            launcher.environment_python(windows, "win32"),
            windows / "Scripts/python.exe",
        )

    def existing_python(self, root):
        python = launcher.environment_python(
            launcher.environment_path(root, sys.platform), sys.platform
        )
        python.parent.mkdir(parents=True)
        python.touch()
        return python

    def test_ready_environment_never_runs_pip_on_restart(self):
        with tempfile.TemporaryDirectory(prefix="qnn demo ") as directory:
            root = Path(directory)
            python = self.existing_python(root)
            with patch.object(
                launcher.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run:
                self.assertEqual(launcher.prepare(root), python)
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0][0], str(python))
                self.assertNotIn("pip", run.call_args.args[0])

    def test_missing_numpy_installs_only_inside_demo_environment(self):
        with tempfile.TemporaryDirectory(prefix="qnn demo ") as directory:
            root = Path(directory)
            python = self.existing_python(root)
            results = [
                subprocess.CompletedProcess([], 1),
                subprocess.CompletedProcess([], 0),
            ]
            with patch.object(launcher.subprocess, "run", side_effect=results) as run:
                launcher.prepare(root)
                command = run.call_args.args[0]
                self.assertEqual(command[:4], [str(python), "-m", "pip", "install"])
                self.assertIn("--only-binary=:all:", command)
                self.assertEqual(command[-1], str(root / "demo" / "requirements.txt"))
                self.assertEqual(run.call_args.kwargs["cwd"], root)

    def test_failed_setup_explains_how_to_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.existing_python(root)
            with patch.object(
                launcher.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 1),
            ):
                with self.assertRaisesRegex(RuntimeError, "run the launcher again"):
                    launcher.prepare(root)

    def test_python_requirements_keep_reference_and_newer_wheels_separate(self):
        self.assertEqual(launcher.numpy_version((3, 12)), "1.26.4")
        self.assertEqual(launcher.numpy_version((3, 13)), "2.4.6")

    def test_launch_from_any_directory_uses_repo_and_available_port(self):
        with patch.object(
            launcher, "prepare", return_value=Path("demo-python")
        ), patch.object(
            launcher.subprocess, "call", return_value=0
        ) as call, patch.object(
            sys, "argv", ["launch_demo.py", "--no-browser"]
        ):
            self.assertEqual(launcher.main(), 0)
            self.assertEqual(
                call.call_args.args[0], ["demo-python", "-m", "demo", "--port", "0"]
            )
            self.assertEqual(call.call_args.kwargs["cwd"], ROOT)


if __name__ == "__main__":
    unittest.main()
