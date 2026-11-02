# Performance scheduling

Tools for ordering the performances in a dance show so that nobody has to perform again too soon.

- **Schedule finder:** works out running orders for you, with optional pins (fix a performance to a slot) and breaks.
- **Schedule checker:** tests a running order you made yourself and shows who would not get enough rest.

You use both from a page in your web browser. The page runs only on your own computer, and your performer file is not sent anywhere.

<!-- Video tutorial: add the link here when it exists, for example "Watch the 5-minute overview: <link>". -->

**New here?** Do the one-time setup below, start the page, then follow the [user guide](docs/user-guide.md).

## Setup (one time)

You need a computer running Windows or macOS, an internet connection for the setup, and a web browser. Python is the only program you have to install. Everything else is downloaded for you in step 4. Allow about 10 minutes.

### 1. Get the project

Download the project as a ZIP file and **extract it** before doing anything else. Running files from inside a ZIP does not work.

- Windows: right-click the ZIP, choose **Extract All**.
- Mac: double-click the ZIP.

Keep the extracted folder somewhere you can find it, such as Documents. If you later move or rename the folder, repeat step 4 (see "If something goes wrong").

### 2. Install Python

Download Python from <https://www.python.org/downloads/> and run the installer. Any version from **3.11 to 3.13** works. It is free and does not need any other program.

- **Windows:** on the first installer screen, tick **Add python.exe to PATH**, then choose **Install Now**.
- **Mac:** use the installer from python.org. Do not rely on the Python that comes with a Mac. It is usually too old (3.9).

Then open a **new** command window (step 3) and check the version:

| Windows (Command Prompt) | Mac (Terminal) |
|---|---|
| `py --version` | `python3 --version` |

You should see `Python 3.11` or higher. If you see an older number or an error, see "If something goes wrong".

### 3. Open a command window in the project folder

- **Windows:** open the project folder in File Explorer, click the address bar at the top, type `cmd` and press Enter. A black window opens, already in the right folder.
- **Mac:** type `cd ` (the letters c, d and a space) in Terminal, drag the project folder from Finder onto the Terminal window, then press Enter. (Terminal is in Applications, then Utilities.)

### 4. Create the private environment and install the packages

This downloads what the page needs (Streamlit and OR-Tools, and the packages they rely on) and keeps them inside a folder called `.venv` in the project, so nothing else on your computer is changed. It needs internet and takes a few minutes. Run the two lines in order, one at a time:

**Windows**

    py -m venv .venv
    .venv\Scripts\python -m pip install -e ".[ui]"

**Mac**

    python3 -m venv .venv
    .venv/bin/python -m pip install -e ".[ui]"

The second line prints a lot of text. When it stops and you see a line starting **Successfully installed**, the setup is done. A message saying a new version of pip is available is harmless.

You only do steps 1 to 4 once on each computer.

## Start the page

**Windows:** double-click **`run_app.bat`** in the project folder. A black window opens, and your browser opens the page a few seconds later.

If Windows says **Windows protected your PC**, choose **More info**, then **Run anyway**. It appears because the file was downloaded.

**Mac:** open Terminal in the project folder (step 3) and run:

    .venv/bin/python -m streamlit run src/performance_scheduling/app.py

Your browser opens the page a few seconds later. Run this from the project folder, because the page's settings are read from there.

If the browser does not open, type `http://localhost:8501` into its address bar. **Keep the black window (or Terminal) open while you work.** To stop the page, close the window (on a Mac press Control and C first, then close Terminal). Closing the browser tab does not stop it.

Next: the [user guide](docs/user-guide.md) takes you from a spreadsheet to a downloaded schedule.

## If something goes wrong

| What you see | What to do |
|---|---|
| `'py' is not recognized` (Windows) | Python is not installed, or the installer's PATH box was not ticked. Run the Python installer again, choose **Modify** or **Uninstall** and reinstall with the box ticked. Then open a new Command Prompt. You can also try `python` instead of `py`. |
| `python3 --version` shows 3.9 or lower (Mac), or a window offers to install "command line developer tools" | Install Python from python.org (step 2). Close Terminal, open a new one, and check again. |
| The version is lower than 3.11 | Install a newer Python from python.org (step 2). Older Pythons are not supported. |
| Step 4 ends with a red error or `Could not find a version`, `Connection`, or `timed out` | Check your internet connection and run the line again. On a work or school network, a firewall may block downloads. Ask your IT help. |
| `run_app.bat` says the page is **not set up** | Do step 4 in this folder. Check the folder `.venv` exists inside it. |
| `run_app.bat` says the page is **missing something** | Run the command it shows, in this folder. |
| The page worked, then stopped working after the folder was moved or renamed | Delete the `.venv` folder and repeat step 4. |
| The browser shows nothing, or "site can't be reached" | Check the black window (or Terminal) is still open and has no error text. Close it and start again. |

Messages inside the page are explained in [docs/error-messages.md](docs/error-messages.md).

## Your data

Real performer names are personal data. Keep your performer file somewhere private, and do not commit it to a shared repository. The rules are in [docs/data-privacy.md](docs/data-privacy.md). The folder `data/examples/` has made-up files you can practise with.

## For developers and collaborators

- [docs/README.md](docs/README.md) is the index of all documents.
- [docs/project-brief.md](docs/project-brief.md) is the entry point: what the project is, where it stands and the key decisions.
- [docs/environment.md](docs/environment.md) describes Python, packages and developer tools.

To run the tests, install the developer extras instead of `.[ui]`, then run `pytest`:

    .venv\Scripts\python -m pip install -e ".[dev]"      (Windows)
    .venv/bin/python -m pip install -e ".[dev]"          (Mac)
