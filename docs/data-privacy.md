# Data privacy

**Status:** DRAFT (2026-10-31). The rules below were confirmed by the project owner on 2026-10-31, except the one marked *(proposed)*. The rest describes what the code and configuration already do, or rules in the decision log (D49, D53, D58, D59).

## 1. What is personal data here

| Data | Personal? | Where it appears |
|---|---|---|
| The performer file: performer names or ids, with the performances each is in | **Yes.** Treat it as personal even when it is described as anonymised: in a show of about 120 people, names or ids can identify someone | `data/private/`; in memory while the page is open |
| The problems file (`<schedule file>_problems.csv`) and the checker's printed report | **Yes.** They name the performers who are not given enough rest | The organiser's Downloads folder; the terminal |
| Schedules found by the finder (`schedules_1-5.csv`, the page's table) | **No.** They list performance names only (for example "Bollywood (Open)") | `output/`; the page |
| A schedule file to be checked | **No.** Performance names only | Wherever the organiser keeps it |
| The synthetic files in `data/examples/` | **No.** Invented ids such as "Person 0001" | Committed to git |

If a performance name ever contains a person's name (for example a solo named after its dancer), treat the schedule files as personal data too.

## 2. Where real files may live

- **Real performer files go in `data/private/` and nowhere else in the project folder (Q12, D58).** `.gitignore` ignores everything in `data/` except `data/examples/`.
- **Only synthetic files go in `data/examples/`.** The tests use only these.
- The finder's output folder `output/` is also ignored by git, but it is not a place for personal data. It holds no names, and the finder never overwrites a file (D43).
- A **problems file** or a copy of a checker report is personal data. Keep it in `data/private/` or delete it when it has been used.

## 3. What is never committed or shared

- Nothing outside `data/examples/` is committed from `data/`. Check before each commit that `git status` shows no file from `data/private/`.
- **Check once that no private file was ever committed.** An ignore rule does not remove a file that was added earlier. Run `git log --all --oneline -- data/private` and `git ls-files data`; the first should print nothing and the second only files under `data/examples/`. Checked on 2026-10-31: both were as expected.
- **Notebooks:** outputs can contain real names. `notebooks/search_experiment.ipynb` reads a real file from `data/private/`, but it prints no performer data or problem messages (checked 2026-10-31), so `nbstripout` is not needed for it. Check a notebook's outputs again before committing if a cell starts to show performer data.
- **Do not paste or attach real performer files, problems files or terminal output containing names** into chats with an AI assistant, a Project's files, bug reports or e-mail. Use a synthetic example that shows the same fault.

## 4. What the page keeps (D49, D53)

| Question | Answer | How it is known |
|---|---|---|
| Where is the uploaded file held? | In the memory of the running page only. Streamlit's upload store is `MemoryUploadedFileManager` (Streamlit 1.66.1) | Read in the installed Streamlit |
| Is anything written to disk? | No, apart from a file the organiser chooses to download. The code never writes files, never uses `st.cache_*` and never uses `persist="disk"` | Searched `app.py` for `persist`, `cache_` and file writes (none; it only reads the example file). No test checks this, so repeat the search after changing the page |
| Are usage statistics sent? | No. `gatherUsageStats = false` in `.streamlit/config.toml`. A first run with a fresh home folder showed no e-mail prompt | Config; tried on Linux |
| Who can open the page? | Only this computer: `server.address = "localhost"` | Config |
| Can an error show a name or a traceback? | Not in the browser: `showErrorDetails = "none"`, and every unexpected error in `app.py` becomes a short message with no names | Config and code |
| How does the data go away? | **Clear all data** empties the session. Closing the launcher window (the black console window that `run_app.bat` opens) stops the page and drops everything in memory. Closing only the browser tab does not stop the page; the data stays in memory in that window until the page's session expires or the window is closed | D53 (3) |

What I have **not** verified: that the page makes no outgoing network connection at all (only that usage statistics are off), and the Windows behaviour of the first run. Two further things are outside the page's control:

- **The downloaded files** (schedules, problems) go to the browser's Downloads folder, outside the project. Move or delete a problems file when finished.
- **Other people logged in to the same computer** (shared computers, remote desktop, a shared login) can open `http://localhost:8501`. Run the page only on a computer you do not share, or close it when you step away.
- **Cloud sync and lost computers.** If the project folder or the Downloads folder is inside OneDrive, Dropbox, iCloud or similar, the files in `data/private/` are copied to that company's servers. Keep the project outside synced folders, or exclude `data/private/` from syncing. Turn on disk encryption (BitLocker on Windows) in case the computer is lost. *(proposed)*

## 5. Logs and error messages

- The page and the commands never write a log file of their own.
- The page shows no names beyond the ones the organiser has already seen on screen (D49).
- The **commands** do print names in their reports, because the user is looking at their own terminal. Treat that output as personal data (section 1).

## 6. Running it for someone else (Q16, D53)

Q16 was answered as "only the project owner uses the page, on one computer".

- To give the folder to another organiser, they run it on **their own computer**. The `.streamlit/config.toml` and the example file travel with the folder. Do not copy `data/private/` with it.
- That person should read this file first. Share the folder as a zip made from a clean checkout so that `data/private/` and `output/` are not in it.
- **Do not host the page** on a shared server or on the internet with real data. That would be a separate decision and would need at least: sign-in, encrypted connections, a decision on who may see which show, a way to delete data on request, and a written agreement with whoever runs the server. It also means changing `server.address`. None of this is built or planned.

## 7. When the show is over

Delete the real performer file and any problems files from `data/private/` and the Downloads folder once the show has run and they are no longer needed. Keep the synthetic examples.

## 8. Checklist before sharing or committing

1. `git status` shows nothing from `data/private/`.
2. No notebook in the commit shows performer data in its outputs.
3. No problems file or report with names is in the folder being shared.
4. The page was started from the project folder (so `config.toml` applied) and with `run_app.bat` or the `streamlit run` command in the README, and not with a changed `--server.address`.
