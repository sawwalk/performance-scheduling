# Error messages

**Status:** DRAFT (2026-10-31). Every message the tools can show, grouped by situation, with what to do. The user guide (`user-guide.md`) uses this wording.

## How messages appear

- **Errors** stop the file or search. On the page they are in a red box; the commands print them under a heading such as "Could not check the schedule:" and exit.
- **Warnings** do not stop anything. The page lists them in a box titled "N things to check"; the commands print them and ask you to review them.
- Each starts with `ERROR:` or `WARNING:` in the commands, and with `row N:` when it is about one row (the header is row 1, as in your spreadsheet).
- A `…` below stands for a value that is filled in when you see the message: a name, a number or a list. The messages are shown in full words as they appear, apart from that.
- Messages never include a traceback. They include the names that are in your own file, so treat a copied message as personal data (`data-privacy.md`).

## What is listed, and how it is kept right

`scripts/list_messages.py` reads the code and finds every message (the rules are at the top of that file). `python scripts/list_messages.py --check` fails if a message in the code has no entry here, or an entry here is no longer in the code, and `tests/test_error_messages.py` runs the same check. Widget labels, `--help` text, table headings and file-name patterns are not messages.

**When you add a message:** add a row to the right section here, with the message in backticks at the start of the row. A repeat of a message in another place is one entry. If the check names a message that is not a message (a label), the rules in `list_messages.py` are what to change.


## 1. A file cannot be opened or read

These stop a file loading. Nothing else is shown until the file is fixed.

| Message | What it means | What to do |
|---|---|---|
| `… could not be read as UTF-8 text. In Excel, use "Save As" and choose "CSV UTF-8".` | The file is not saved as UTF-8 text. Older Excel "CSV" files often are not. | In Excel choose *Save As*, then *CSV UTF-8 (Comma delimited)*, and load the file again. |
| `File not found: …` | The path given to a command does not lead to a file (commands only). | Check the spelling and the folder. Put the path in quotes if it contains spaces. |
| `Could not read …: …` | The file exists but could not be opened, for example because another program has it open or you may not read it. | Close it in Excel, check that you may open it, or try a copy of the file. |
| `The file is empty.` | The file has no content at all, not even a header row. This can be the performer, schedule or fixed-positions file. | Check that you chose the right file, and save it again from your spreadsheet. |
| `No usable rows were found.` | The performer file has a header, but no row has both a performer and a performance. | Look for the warnings "missing …; row dropped" (section 3), and check the columns chosen. |

## 2. Choosing the performer and performance columns

The page asks you to pick the two columns. The commands use `--id-column` and `--performance-column`.

| Message | What it means | What to do |
|---|---|---|
| `Choose the two columns to continue.` | The page does not guess which columns to use, so nothing loads until both are chosen. | Pick the performer column and the performance column in the two lists. |
| `Give both the performer column and the performance column, or neither.` | Only one of `--id-column` and `--performance-column` was given (commands only). | Give both options, or neither if the file has exactly two columns. |
| `Expected exactly two columns (performer, then performance) but found …: …. Say which columns to use.` | The file has more or fewer than two columns, so the tool cannot tell which two to use. | Name the two columns (pick them on the page, or use the two options), or delete the extra columns. |
| `Column "…" not found. Columns in the file: ….` | A named column is not in the file. The message lists the columns that are. | Use one of the names listed, spelled the same way. |
| `Column "…" appears more than once in the file.` | Two columns have the same heading, so the name does not say which is meant. | Rename one of the headings in the file. |
| `The performer column and the performance column are the same.` | The same column was chosen for both. | Choose two different columns. |
| `Ignoring other column(s): ….` | Warning. The file has more columns than the ones used (or, in a pins file, more than `position` and `item`). They are not read. | Nothing, unless you meant one of them to be used. |

## 3. Rows in the performer file

Warnings do not stop the file loading; the page shows them in a box titled "N things to check", and the commands ask you to review them. The tool tells you what it did with the row.

| Message | What it means | What to do |
|---|---|---|
| `missing …; row dropped` | Warning. The row has no performer or no performance (the message says which), so it is left out. | Fill in the missing cell if the row matters. A left-out row means that performer is not protected from back-to-back performances. |
| `duplicate of an earlier row (…, …); ignored` | Warning. The same performer and performance were listed twice. The second row is ignored. | Nothing, unless the repeat is a typing slip for a different row. |
| `"…" is a reserved word (it marks a break). Rename the performance.` | Error. A performance is called `BREAK`, which is the word the tool uses for a break. | Rename the performance in the file. |
| `Performer ids "…" and "…" look very similar. If they are the same person, correct the file so the spelling matches; otherwise ignore this.` | Warning. Two ids are spelled almost the same, so they might be one person typed twice. They are treated as two people. | If they are the same person, correct the spelling so they match. Otherwise ignore the warning. |
| `Performance names "…" and "…" look very similar. If they are meant to be one performance, correct the file so the spelling matches.` | Warning. Two performance names are spelled almost the same. They are treated as two performances. | If they are one performance, correct the spelling so they match. Otherwise ignore the warning. |

## 4. The schedule file (Check a schedule)

A schedule file has a `position` column and one or more columns with a running order. Errors are shown with the row number as you see it in your spreadsheet (the header is row 1).

| Message | What it means | What to do |
|---|---|---|
| `Column(s) … in the header row have no name.` | A column in the header row has no heading. | Give the column a name, or delete the column. |
| `More than one column is called "position".` | Two columns are called `position`. Also shown for a fixed-positions file. | Keep one `position` column. |
| `The file has no schedule columns, only the position column.` | The file has a `position` column and nothing else. | Add a column holding a running order. |
| `Two schedule columns are called "…" and "…". Give each schedule its own name.` | Two schedules have the same name. | Give each schedule column its own name. |
| `The file has no schedule rows.` | There is a header but no data rows. | Add the rows, or load the right file. |
| `has more cells than the header has columns; the extra cells are ignored` | Warning. A row has more cells than the header has columns. The extra cells are ignored. | Delete the extra cells, or add a heading for them. |
| `position …` | The first part of the two position messages below (it is shown with the row number). | See the next two entries. |
| `"…" is not a whole number` | The `position` cell holds something that is not a whole number such as 1, 2, 3. Also used by the commands for a number option. | Type the position as a whole number. |
| `is missing` | The `position` cell is empty. Shown after the word position, for example "position is missing". | Fill in the position. |
| `position … is repeated (also used in row …)` | Two rows have the same position. | Renumber so that each position is used once. |
| `Positions must be numbered 1 to … with no gaps (the file has … rows). Missing: …. Not expected: ….` | The positions skip a number or do not start at 1. The message lists which are missing and which are unexpected. | Number the rows 1, 2, 3 and so on with no gaps. |
| `empty slot in "…" treated as a break` | Warning. A cell in that schedule column is empty, and counts as a break. | If you meant a break, nothing to do. If not, fill in the performance. |

## 5. A schedule does not match the show

The schedule is read, but it does not line up with the performer file. Spacing is not checked until this is fixed.

| Message | What it means | What to do |
|---|---|---|
| `"…" is in the schedule (position …) but not in the performer file.` | A performance in the schedule is not in the performer file. | Check the spelling, or add the performance to the performer file (a performance nobody is in is not listed there). |
| `Did you mean "…"?` | Added to the message above (or to an unknown pin) when a similar name exists in the performer file. | If it is the right one, correct the spelling in your file. |
| `"…" appears … times in the schedule (positions …). Each performance should appear once.` | A performance is in the schedule more than once. | Remove the repeats. |
| `"…" is in the performer file but missing from the schedule.` | A performance with performers is not in the running order. | Add it to the schedule. |
| `Spacing was not checked.` | Printed above the problems with the schedule itself. Because of them, the tool did not check rest between performances. | Fix the problems listed, then check again. |
| `No schedule column called "…". Columns found: ….` | The `--schedule-column` named in the command is not in the schedule file (command only). | Use one of the columns listed. |

## 6. Reading the result of a check

These are not errors. They say whether the schedule is valid and how tight it is.

| Message | What it means | What to do |
|---|---|---|
| `All … schedules are valid.` | Every checked schedule keeps the required rest. | Nothing. |
| `All … schedules are invalid.` | No checked schedule keeps the required rest. | See the conflicting pairs and who is affected for each. |
| `… of … schedules are invalid.` | Some schedules are valid and some are not. | Look at the schedules named invalid. |
| `Tightest spacing: … between a performer's performances.` | The smallest number of slots between two performances of the same performer in this schedule. | Compare it with the rest you asked for. |
| `No performer is in more than one performance, so spacing does not apply.` | Nobody appears twice, so rest between performances cannot be a problem. | Nothing. |
| `Valid schedules are listed in the table only.` | With more than 10 schedules, only invalid ones are written out in full. | Nothing. |
| `Violations written to … (… row…).` | The commands wrote the list of problems to the file named by `--report-csv`. | Open the file. It lists performer names, so keep it private (see data-privacy.md). |
| `Please review these … warning(s) about the performer file:` | Printed by the checker before its result when the performer file had warnings. | Read the warnings (section 3). |
| `Please review these … warning(s) about the schedule file:` | The same, for the schedule file. | Read the warnings (section 4). |
| `Please review these … warning(s) about the … file:` | The same, in the finder, for the performer or fixed-positions file. | Read the warnings (sections 2, 3 and 7). |

## 7. The fixed-positions (pins) file

A pins file has a `position` column and an `item` column. A pin fixes a performance or a `BREAK` to a slot.

| Message | What it means | What to do |
|---|---|---|
| `No "position" column. Columns in the file: ….` | The file has no `position` column. | Add it, or load the right file. |
| `No "item" column. Columns in the file: ….` | The file has no `item` column. | Add it, or load the right file. |
| `More than one column is called "item".` | Two columns are called `item`. | Keep one. |
| `position is missing` | A pin has no position. | Fill it in. |
| `position "…" is not a whole number` | A pin's position is not a whole number. | Use whole numbers. |
| `position 0 is not allowed: positions start at 1` | Slots are numbered from 1. | Start at 1. |
| `item is missing` | A pin has a position but no performance. | Fill in the performance or `BREAK`, or delete the row. |
| `"…" is pinned more than once (also in row …)` | Two rows pin the same item. The message names the other row. | Keep one pin for it. |
| `The file has no pinned rows, so nothing is pinned.` | The file is empty apart from the header, so nothing is pinned. | Add pins, or leave the file out. |

## 8. Which schedules to show, and the other settings

On the page, the "Which schedules" box gives these messages under it, and the search does not start. The commands use `--pick`, `--gap`, `--breaks`, `--limit`, `--seed` and `--time-limit`.

| Message | What it means | What to do |
|---|---|---|
| `Use numbers, ranges and commas, for example 1,4,9 or 1-3, 7 or the word all.` | Added to each pick message to show what is accepted. | Write for example `1-5`, `1,4,9`, `1-3, 7` or `all`. |
| `Nothing was chosen.` | The pick is empty. | Type a pick, or press *Select all*. |
| `There is an empty item (two commas in a row, or a comma at the start or end).` | There are two commas in a row, or a comma at the start or end. | Remove the extra comma. |
| `"all" cannot be combined with numbers. Use it on its own.` | `all` was mixed with numbers. | Use `all` on its own. |
| `"…" is not a number or a range.` | Part of the pick is not a number such as 4 or a range such as 1-3. | Correct that part. |
| `Numbers start at 1 (found "…").` | A number below 1 was given. | Start at 1. |
| `The range "…" goes backwards. Write it as …-….` | A range such as 5-2 was given. | Write it the other way round, as the message says. |
| `"…" is too high: the highest available number is ….` | A number is above the last schedule that can be chosen. | Choose a number up to the one shown. |
| `That chooses … items but the most allowed at once is …. Choose fewer, or raise the limit.` | The pick asks for more schedules than one run may write. | Choose fewer, or raise *Most schedules per run* (`--limit`). |
| `the gap cannot be negative` | `--gap` was below 0 (commands only). | Use 0 or more. |
| `this must be at least 1` | A command option such as `--limit` was below 1. | Use 1 or more. |
| `this must be more than 0` | `--time-limit` was 0 or less. | Give a number of seconds above 0. |
| `"…" is not a number` | `--time-limit` was not a number. | Give a number of seconds. |

## 9. Pins that cannot work

Found before the search starts, so it does not run. They are shown as errors with the finder's other problems.

| Message | What it means | What to do |
|---|---|---|
| `The pin at slot … (…) is outside the show: there are … slots (… and …).` | A pin is at a slot higher than the number of performances plus breaks. | Move the pin, or raise the number of breaks. |
| `The pin at slot … names "…", which is not in the performer file.` | A pin names a performance that is not in the performer file. | Check the spelling. |
| `"…" is pinned to more than one slot (…).` | The same performance is pinned to two slots. | Remove one of the pins. |
| `… … pinned as breaks, but the show has only …. Raise the number of breaks or remove a pinned break.` | More slots are pinned as breaks than there are breaks. | Raise the number of breaks or remove a pinned break. |
| `The pins at slots … and … (… and …) clash: they share …, so they need at least … between them but have ….` | Two pinned performances share a performer and are too close for the gap. | Move one pin further away or lower the gap. |
| `The schedule finder needs OR-Tools, which is not installed. Install it with: pip install -e ".[finder]"` | The command could not start because the search engine is not installed. | Run `pip install -e ".[finder]"` in the project folder. |
| `The schedule finder is not installed on this computer. Ask whoever set it up to install it.` | The same, on the page. | Ask whoever set it up to install it. |

## 10. No schedule can exist

Worked out before searching, or when the search finishes without a result. The reason is listed under the heading.

| Message | What it means | What to do |
|---|---|---|
| `No schedule exists.` | Heading of the box shown when the search finished and found nothing. | Read the reasons under it. |
| `No schedule was found before the time limit.` | Heading when time ran out before anything was found. | Search for longer, or relax the settings. |
| `… … in … performances; with a gap of … that needs at least … slots, but the show has ….` | One performer is in so many performances that they cannot be spaced out in the number of slots. | Raise the number of breaks or lower the gap. |
| `… performances all clash with each other (…). With a gap of … they need at least … slots, but the show has ….` | A group of performances shares performers so that every pair must be apart, and there are not enough slots. | Raise the number of breaks or lower the gap. |
| `No schedule exists with these pins. These pins cannot all be kept at the same time: …. Remove or move at least one of them.` | Each pin is possible alone, but the listed pins cannot all be kept. | Remove or move at least one of the listed pins. |
| `No schedule exists with a gap of … and ….` | No schedule exists with these settings and the pins, and the pins responsible could not be worked out in time. | Remove pins, raise the breaks or lower the gap. |
| `Which pins are the problem could not be worked out.` | The warning that goes with the message above. | Remove pins one at a time to find the cause. |
| `even without the pins` | Added to the message below when the settings alone cannot work, before the pins matter. | Change the gap or breaks. |
| `No schedule exists with a gap of … and ……. …` | No schedule exists for these settings. The advice follows. | Follow the advice. |
| `Try more breaks or a smaller gap.` | The advice added to the message above. | Raise *Breaks* or lower the gap. |
| `These cannot all be kept` | Marks the pins named in "No schedule exists with these pins" in the page's pin list. | Remove or move one of the marked pins. |

## 11. Results and notices from the finder

Not errors. They say what was found and whether there could be more.

| Message | What it means | What to do |
|---|---|---|
| `Found … (… …).` | How many schedules were found, and their numbers (the page). | Nothing. |
| `Wrote … (… …) to ….` | The same, for the command, with the file's path. | Open the file. |
| `More schedules exist after number ….` | The finder's list goes on beyond the last number shown. | Press *Show the next 5*, or run the command it prints. |
| `There … … in all.` | That is the whole list: there are no more. | Nothing. |
| `The search stopped at the time limit after …, so more may exist.` | The time ran out, so more schedules may exist. | Search for longer. |
| `The time limit of … seconds was reached before the search finished. This does not show that no more schedules exist.` | The time ran out before the search finished. It does not show that no more schedules exist. | Search for longer. |
| `Schedule … does` | The first words of the next two messages ("Schedule 7 does"; with several, "Schedules 7, 8 do"). | See the next two entries. |
| `Schedules … do` | As above, for more than one number. | See the next two entries. |
| `… not appear to have been reached before the time limit.` | The numbers asked for were not reached because the search stopped. | Search for longer. |
| `… not exist: there … only ….` | The numbers asked for are higher than the number of schedules that exist. | Choose lower numbers. |
| `Schedules found with a gap of …. To see whether everyone could have a longer rest, run again with a gap of ….` | Offers to try a longer rest next time. | Try the larger gap if you want more rest. |
| `Settings changed. Press Find schedules to update.` | The page: the table shown is from earlier settings and is faded. | Press *Find schedules*. |
| `Searching for up to … seconds...` | The page is searching. | Wait. |
| `Nothing was written.` | The command printed this because no schedule was found. | See the reasons printed with it. |
| `To write the next …, run:` | The command shows the line to run for the next batch. | Copy and run it. |
| `(Each run writes at most …; change that with --limit.)` | A reminder of the `--limit`. | Change it with `--limit` if you want more. |
| `Seed: …. Search engine: OR-Tools ….` | The page's note under the table: the order used and the search engine's version. | Nothing. |
| `Search engine: OR-Tools … (schedule numbers can change if this changes)` | The same, for the command. | Schedule numbers can change if the engine changes, so note the version. |

## 12. Writing files

Commands only.

| Message | What it means | What to do |
|---|---|---|
| `… already exists. Schedules are never written over an existing file: choose another folder, or move or delete the file.` | The finder never writes over an existing file. | Choose another folder with `--out`, or move or delete the file. |
| `Could not write …: the folder could not be created (…)` | The output folder could not be made (the reason follows). | Check the folder's name and that you may write there. |
| `Could not write …: …` | The file could not be written (the reason follows). | Close it if it is open elsewhere, or check permissions and space. |

## 13. Lines that introduce results (not problems)

Printed or shown before the results, so you can see what was used.

| Message | What it means | What to do |
|---|---|---|
| `Performer file: … (… performers, … performances)` | The file name, with its numbers of performers and performances. | Check they look right. |
| `Schedule file: … (… schedule…)` | The file name and how many schedules it has. | Check they look right. |
| `Gap checked: … (…)` | The rest required between a performer's performances. | Check it is what you meant. |
| `Fixed positions: … (…)` | The pins file and the number of pins. | Check it is what you meant. |
| `Settings: gap …, … (… slots), …` | The gap, breaks, slots and order the finder used. | Check it is what you meant. |

## 14. Headings that wrap other messages

A heading with a list of problems under it.

| Message | What it means | What to do |
|---|---|---|
| `Could not check the schedule:` | The checker's heading for its errors. | Read the list under it. |
| `Could not run the schedule finder:` | The finder's heading for its errors. | Read the list under it. |
| `This file cannot be used` | The page's red box for a performer file that cannot be read. Every error is listed. | Fix the errors and load the file again. |
| `The schedule file … cannot be used` | The same for a schedule file. | Fix the errors and load the file again. |
| `… to check in …` | The heading of the warnings box, for example "2 things to check in this file". | Read the warnings; nothing is stopped. |
| `**Problems with the schedule itself (…)** … …` | The page's red box for a schedule with structural problems. | Fix them (section 5). |

## 15. Something unexpected went wrong

These should not happen. The page shows a short message, never a traceback, and no names (D49).

| Message | What it means | What to do |
|---|---|---|
| `Something unexpected went wrong while reading this file, so it was not loaded. Check that it is a CSV file saved as "CSV UTF-8", or ask whoever set this up.` | An unexpected failure while loading a performer or schedule file. | Check the file is a CSV saved as CSV UTF-8. If it happens again, ask whoever set the page up, and tell them what you did. Do not send the real file. |
| `Something unexpected went wrong while checking this schedule, so no result is shown. Ask whoever set this up.` | An unexpected failure during a check. | Ask whoever set the page up. |
| `Something unexpected went wrong while searching, so no schedule is shown. Ask whoever set this up.` | An unexpected failure during a search. | Ask whoever set the page up. |
| `Something went wrong inside the finder, and no schedule was shown.` | The finder reported a fault in itself (one of the four "Internal error" messages). The page offers details to copy. | Copy the details into a bug report (without names). |
| `Internal error: … failed the schedule checker.` | The finder produced a schedule that its own checker rejects. It is not shown. | Report it as a bug, with the settings. |
| `Internal error: … has the wrong number of breaks.` | As above: the wrong number of breaks. | Report it as a bug. |
| `Internal error: … does not keep the pins.` | As above: a pin was not kept. | Report it as a bug. |
| `Internal error: … repeats an earlier schedule.` | As above: a repeat. | Report it as a bug. |
| `The solver rejected the model: …` | The search engine found the model invalid. | Report it as a bug. |

## 16. Mistakes by a programmer (not shown in normal use)

Raised when code calls a function with an impossible value. The commands and the page check their inputs first, so an organiser should not see these. If one appears, it is a bug.

| Message | What it means | What to do |
|---|---|---|
| `there are no schedules to write` | `write_schedules` was given none. | Report it. |
| `there are no schedules to report` | `format_found` was given a count below 1. | Report it. |
| `all schedules must have the same number of slots` | `write_schedules` was given schedules of different length. | Report it. |
| `schedule name "…" cannot be used as a column heading (it is empty, is "position", or repeats another name)` | A schedule has an empty name, `position`, or the name of another. | Report it. |
| `"all" has no fixed list of numbers` | A function that needs a list was given `all`. | Report it. |
| `gap cannot be negative` | A function was given a negative gap. | Report it. |
| `breaks cannot be negative` | A function was given negative breaks. | Report it. |
| `count must be at least 1` | `find_schedules` was asked for fewer than 1 schedule. | Report it. |
| `time_limit must be positive` | `find_schedules` was given a time limit of 0 or less. | Report it. |
| `the show has no performances` | `find_schedules` was given a show with no performances. | Report it. |
