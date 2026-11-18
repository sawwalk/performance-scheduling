# Performance scheduling

Tools for ordering the performances in a dance show so that nobody has to perform again too soon.

- **Schedule finder:** works out running orders for you, with optional pins (fix a performance to a slot) and breaks.
- **Schedule checker:** tests a running order you made yourself and shows who would not get enough rest.

You use both from a page in your web browser. The page runs only on your own computer, and your performer file is not sent anywhere.

**New here?** Do the one-time setup below, start the page, then follow the [user guide](docs/user-guide.md).

## Setup (one time)

If you use Windows you can watch the [setup video](docs/video_tutorials/one-time-setup-windows.mp4) or play directly from performance-scheduling-main/docs/video_tutorials/one-time-setup-windows.mp4. The written steps below are the full reference, and the only guide for a Mac.

You need a computer running Windows or macOS, an internet connection for the setup, and a web browser. Python is the only program you have to install. Everything else is downloaded for you in step 4. Allow about 10 minutes.

### 1. Get the project

Download the project as a ZIP file and **extract it** before doing anything else. Running files from inside a ZIP does not work.

- Windows: right-click the ZIP, choose **Extract All**.
- Mac: double-click the ZIP.

Keep the extracted folder somewhere you can find it, such as Documents. If you later move or rename the folder, repeat step 4 (see "If something goes wrong").

### 2. Check or install Python

This project works with **Python 3.11, 3.12, 3.13 or 3.14**. **Python 3.13 is the recommended choice.** Do not use Python 3.15 or newer. The big yellow button on the python.org front page always offers the newest Python, and this project cannot use a version that new yet: one of its packages (OR-Tools) is not available for it, and step 4 fails with `No matching distribution found for ortools`.

**a. Find out whether Python is already installed.** Open a command window (step 3 below explains how), then run:

| Windows (Command Prompt) | Mac (Terminal) |
|---|---|
| `python --version` | `python3 --version` |

**b. Decide what to do, based on what you see:**

| What you see | What to do |
|---|---|
| `Python 3.11.x`, `3.12.x`, `3.13.x` or `3.14.x` | Python is ready. Skip to step 3. |
| `Python 3.15` or higher | Do **not** uninstall it. Install Python 3.13 alongside it, as described below. The two versions live side by side. In step 4 you will tell the setup to use 3.13. |
| A version lower than 3.11 (a Mac usually comes with 3.9), an error, or the Microsoft Store opens | Install Python 3.13, as described below. |

**c. Install Python 3.13 (only if the table above says to).**

1. Go to <https://www.python.org/downloads/windows/> (Windows) or <https://www.python.org/downloads/macos/> (Mac).
2. Find the newest **Python 3.13.x** in the list and download its installer (Windows: *Windows installer (64-bit)*; Mac: *macOS 64-bit universal2 installer*).
3. Run the installer. It is free and does not need any other program.

- **Windows:** on the first installer screen, tick **Add python.exe to PATH**, then choose **Install Now**.
- **Mac:** use the installer from python.org. Do not rely on the Python that comes with a Mac. It is usually too old (3.9).

**d. If you installed 3.13 alongside a newer Python, check that 3.13 is available.** Open a **new** command window and run:

| Windows (Command Prompt) | Mac (Terminal) |
|---|---|
| `py -3.13 --version` | `python3.13 --version` |

You should see `Python 3.13.x`. Ignore what `python --version` or `python3 --version` says. It may still show the newer version, and that is fine, because step 4 names 3.13 directly.

If you installed 3.13 because you had no suitable Python at all, open a new command window and repeat part (a). You should now see 3.13.x.

### 3. Open a command window in the project folder

- **Windows:** open the project folder in File Explorer, click the address bar at the top, type `cmd` and press Enter. A black window opens, already in the right folder.
- **Mac:** type `cd ` (the letters c, d and a space) in Terminal, drag the project folder from Finder onto the Terminal window, then press Enter. (Terminal is in Applications, then Utilities.)

### 4. Create the private environment and install the packages

This downloads what the page needs (Streamlit and OR-Tools, and the packages they rely on) and keeps them inside a folder called `.venv` in the project, so nothing else on your computer is changed. It needs internet and takes a few minutes. Run the lines in order, one at a time.

**Line 1: create the environment.** Choose the version that matches your situation.

*Your `python` / `python3` command shows 3.11 to 3.14 (the normal case):*

| Windows | Mac |
|---|---|
| `python -m venv .venv` | `python3 -m venv .venv` |

*You installed Python 3.13 alongside a newer Python (3.15 or higher), so you need to name 3.13:*

| Windows | Mac |
|---|---|
| `py -3.13 -m venv .venv` | `python3.13 -m venv .venv` |

If a `.venv` folder already exists from an earlier attempt that failed, delete it first, then run the line.

**Line 2: install the packages.**

**Windows**

    .venv\Scripts\python -m pip install -e ".[ui]"

**Mac**

    .venv/bin/python -m pip install -e ".[ui]"

This line prints a lot of text. When it stops and you see a line starting **Successfully installed**, the setup is done. A message saying a new version of pip is available is harmless.

**Line 3 (optional): confirm which Python the environment uses.**

**Windows**

    .venv\Scripts\python --version

**Mac**

    .venv/bin/python --version

You should see a version from 3.11 to 3.14. If you see 3.15 or higher, delete the `.venv` folder and repeat step 4, using the 3.13 version of line 1.

You only do steps 1 to 4 once on each computer.

## Start the page

**Windows:** double-click **`run_app.bat`** in the project folder. A black window opens, and your browser opens the page a few seconds later.

If Windows says **Windows protected your PC**, choose **More info**, then **Run anyway**. It appears because the file was downloaded.

**Mac:** open Terminal in the project folder (step 3) and run:

    .venv/bin/python -m streamlit run src/performance_scheduling/app.py

Your browser opens the page a few seconds later. Run this from the project folder, because the page's settings are read from there.

The first time the page starts on a computer, a line asking for an **Email** may appear in the window. You do not need to give one: press **Enter** to skip it, and the page starts.

If the browser does not open, type `http://localhost:8501` into its address bar. **Keep the black window (or Terminal) open while you work.** To stop the page, close the window (on a Mac press Control and C first, then close Terminal). Closing the browser tab does not stop it.

Next: the [user guide](docs/user-guide.md) takes you from a spreadsheet to a downloaded schedule.

## If something goes wrong

| What you see | What to do |
|---|---|
| `'python' is not recognized` (Windows), or the Microsoft Store opens | Python is not installed, or the installer's PATH box was not ticked. Install Python 3.13 from python.org (step 2) with **Add python.exe to PATH** ticked, then open a new Command Prompt. If `py --version` works but `python --version` does not, use `py` instead of `python` in step 4. |
| `python3 --version` shows 3.9 or lower (Mac), or a window offers to install "command line developer tools" | Install Python 3.13 from python.org (step 2). Close Terminal, open a new one, and check again. |
| The version is lower than 3.11 | Install Python 3.13 from python.org (step 2). Older Pythons are not supported. |
| The version is 3.15 or higher, or step 4 ends with `No matching distribution found for ortools` | Your Python is too new. **Do not uninstall it.** Install Python 3.13 alongside it (step 2, part c) and check it with `py -3.13 --version` (Windows) or `python3.13 --version` (Mac). Then delete the `.venv` folder, run the 3.13 version of line 1 in step 4 (`py -3.13 -m venv .venv` on Windows, `python3.13 -m venv .venv` on a Mac), and run line 2 again. |
| `py -3.13` says `No suitable Python runtime found` (Windows), or `python3.13: command not found` (Mac) | Python 3.13 is not installed yet, or the window was opened before it was installed. Install Python 3.13 from python.org (step 2, part c), open a **new** command window, and try again. |
| Step 4 line 3 shows 3.15 or higher | The environment was created with the wrong Python. Delete the `.venv` folder and repeat step 4 with the 3.13 version of line 1. |
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


## AI Diligence Statement

This project was created with the help of Claude AI, which was used for designing the project's structure, gathering requirements, writing code, debugging and creating documentation. I affirm that all AI-generated content and its outputs have been reviewed by a human and reflect my intention, and I take full responsibility for the work done by AI. This statement acknowledges the contribution of AI in this project.
