# Start the demo here

Download the repo and **extract the ZIP first**, or use your Git checkout.
Keep this folder inside the repo; the launchers need the `demo` folder beside it.

| Computer | Launcher |
|---|---|
| Windows | Double-click **Launch Demo.bat**. WSL is not needed. |
| macOS | Double-click **Launch Demo.command** to open it in Terminal. |
| Linux / WSL | Run `sh "ONE-CLICK-LAUNCHERS/Launch Demo.command"` from the repo folder. |

Python 3.10–3.14 must be installed. **Python 3.12 is the reference version.**
If Python is missing, install it from https://www.python.org/downloads/ and
run the launcher again. On Windows, include the Python launcher when installing.

The first launch creates a private Python environment and installs NumPy.
**Internet is needed for that first setup.** Later launches work offline with
the bundled model and images. No Colab, training, Git, Node, or dataset download
is needed to present.

The browser opens automatically. Select **Start guided tour**, then **Next →**.
Keep the terminal window open while presenting. Press **Ctrl+C** there to stop.
If the browser does not open, copy the printed `http://127.0.0.1:...` address.
The launcher chooses an available port each time.

## If double-clicking does not work

From a terminal in the repo folder:

```text
python ONE-CLICK-LAUNCHERS/launch_demo.py
```

Use `python3` on macOS/Linux if needed. This runs the same setup and demo.
If macOS reports that the `.command` file is not executable, use
`sh "ONE-CLICK-LAUNCHERS/Launch Demo.command"` from Terminal instead.

Run the launcher once **before presentation day**, then try it again with Wi-Fi
off. The [demo guide](../demo/README.md) has the speaking route, setup help,
and calculation checks.
