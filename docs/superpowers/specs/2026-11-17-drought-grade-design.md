# Drought grade (short design)

**Why:** readers should see at a glance how hard drought is hitting their county right now, on the same A–F scale as power.

**Decided with Marisela (Nov 17, 2026):**
- Drought is graded by the U.S. Drought Monitor level that covers at least half of the county (the "status" the drought card already shows).
- None = A, D0 abnormally dry = B, D1 moderate = C, D2 severe = D, D3 extreme or D4 exceptional = F.
- The drought grade counts in the overall grade (average with power).
- Data centers stay ungraded for now: the list only covers Meta's sites, so a grade would make most counties look better than they are.
- The grading rules are explained in the FAQ answer "How are the grades decided?"

**Approaches considered:**
- Majority level (chosen): matches the card's status label; a small corner of extreme drought doesn't fail a mostly green county.
- Worst level present (≥1% of land): harsher, 46 F's instead of 27 this week.
- Graded in the spreadsheet by the team: kept as an override. A "Drought Grade" column, if added, takes priority over the computed grade.

**Builder's calls:** draft "What this means for you" text for each drought grade (marked DRAFT for the team to rewrite); the grade updates whenever the drought tab is refreshed.
