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

## Changing the wording
Open `index.html`. The `CONFIG` section at the top of the script holds the column names, and the draft "What this means for you" text for each grade. Edit the text there.

## Other files
- `data/tx-counties.json`: county shapes for the map (Texas Water Development Board).
- `data/tx-zips.json`: which counties each ZIP code covers (U.S. Census Bureau, 2020).
