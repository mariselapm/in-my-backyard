# In My Backyard

A guide to power, water and data centers in every Texas county, with a letter grade for each category.

## Preview it
Double-click `start.command`. It opens http://localhost:8767 in your browser.

## Where the data lives
The site reads **`data/master.xlsx`**. To update the site, replace that file with a new version that keeps the same column names.

**Tab 1, one row per county.** The column names the site looks for:

| What | Column name |
|---|---|
| County name (without "County") | `County` |
| Population | `Population` (anything after it is fine, e.g. "Population (Census Bureau 2025 estimates)") |
| Area | `Square Mileage` |
| Power grade (A–F) | `Reliability Grade` |
| Power facts | `Outage Events`, `Net Generation`, `Power Plants` |
| Water grades (A–F) | `Water Quality Grade`, `Drought Grade`, `Water Capacity Grade` (the site averages them into the water grade), or a single `Water Grade` |
| Data center grade (A–F) | `Data Center Grade` |
| Data center facts | `Data Centers` |

When a grade column is added, that category shows up on the map, the county pages and the comparisons. Until then it says "Not graded yet".

**Optional "Stories" tab** for the "Top stories this month" section. It has the columns `County`, `Title`, `Outlet`, `Link`, `Date` and `Topic`. Put `Statewide` as the county for a story that should show on every county page.

## Top stories (found automatically)
Run `python3 scripts/fetch_stories.py` from this folder (about 10 minutes). It refreshes:
- `data/stories.json`: up to 8 stories from the last 30 days per county, each tagged Power, Water, Drought, Data centers or Environment, with the county's own newspapers first. Also includes statewide stories.
- `data/outlets.json`: local newspapers for each county (Texas Press Association 2023 directory via Wikipedia, matched to counties with Census data).

To refresh just a few counties: `python3 scripts/fetch_stories.py Travis Hood`.
To leave out a bad source, add its name to `SKIP_SOURCES` near the top of the script.
Counties with few stories also show stories from neighboring counties and from across Texas.

## Where to speak up (public meetings)
Each county page has a "Where to speak up" section, and a button at the top that jumps to it and shows the next meeting date. It reads **`data/meetings.xlsx`** (a separate file, so replacing `master.xlsx` doesn't erase it). One row per public body:

| Column | What goes in it |
|---|---|
| `County` | County name without "County" |
| `Type` | `Commissioners court`, `City council`, `Groundwater district` or `Subsidence district` (any other type works too, e.g. a second city or a river authority) |
| `Name` | e.g. `Palestine City Council` |
| `Schedule` | Written like `2nd and 4th Monday of the month, 9 a.m.` or `Every Tuesday, 9 a.m.` The site works out the next meeting date from this. Leave blank if unknown. |
| `Where` | Room and address |
| `Agenda link`, `Website` | Where agendas are posted, and the main site |
| `Covers` | For districts: how much of the county they cover |
| `Checked by` | Initials of the teammate who confirmed the row on the official site |

The first version (Nov. 12, 2026) lists 254 commissioners courts, 238 county-seat city councils (16 county seats aren't incorporated cities), and 202 groundwater and subsidence district rows. Schedules were found on official websites for 47 courts and 23 councils; the rest say "Check the agenda page" until the team fills them in. Websites came from Wikidata; districts from the Texas Water Development Board's district list and its 2019 district map.

## Changing the wording
Open `index.html`. The `CONFIG` section at the top of the script holds the column names, and the draft "What this means for you" text for each grade. Edit the text there.

## Other files
- `data/tx-counties.json`: county shapes for the map (Texas Water Development Board).
- `data/tx-zips.json`: which counties each ZIP code covers (U.S. Census Bureau, 2020).
