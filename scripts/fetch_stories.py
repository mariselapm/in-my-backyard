#!/usr/bin/env python3
"""Find this month's environment stories for every Texas county.

Run it from the project folder:   python3 scripts/fetch_stories.py
It writes:
  data/outlets.json  - local newspapers for each county
  data/stories.json  - up to 8 recent stories per county, plus statewide stories

How it works
  1. Local outlets: the Texas newspaper list on Wikipedia (from the Texas Press Association's
     2023 directory) gives each paper's city; the Census place-by-county file gives each city's county.
  2. Stories: one Google News search per county for the last 30 days, using the county name and
     its newspaper towns plus topic words. Only headlines that name a topic AND either the place
     or a local outlet are kept, so unrelated stories are filtered out.
Uses only the Python standard library.
"""
import json, re, sys, time, collections, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "Mozilla/5.0 (In My Backyard student news prototype)"}
PER_COUNTY = 8
PAUSE = 1.5  # seconds between searches, to be polite

# Topic words -> category. Order matters: the first category that matches a headline wins.
CATEGORIES = [
    ("Data centers", r"data cent(er|re)s?|datacenter|hyperscale|\bAI campus|bitcoin min|crypto min"),
    ("Drought", r"drought|burn ban|wildfire|grass fire|dry conditions|rainfall deficit"),
    ("Water", r"\bwater\b(?! rescue)|aquifer|reservoir|groundwater|wastewater|boil(-| )water|lake levels?|\bwells?\b|river authority|desalination"),
    ("Power", r"\bpower\b(?!ful| play| ranking)|power grid|\bgrid\b|ERCOT|outage|electric|electricity|blackout|\bsolar\b|wind farm|wind turbine|transmission line|natural gas plant|power plant|utility rates?|Oncor|CenterPoint"),
    ("Environment", r"pollution|air quality|emissions|oil spill|flaring|\bflare\b|environment|TCEQ|\bEPA\b|climate|landfill|chemical|toxic|contaminat|hurricane|flood|wildlife|conservation|endangered|pipeline"),
]
CAT_RE = [(c, re.compile(p, re.I)) for c, p in CATEGORIES]
# Headlines about elections use "power" as a figure of speech; skip them unless a stronger topic matches.
OFF_TOPIC = re.compile(r"election|ballot|polling|voter|campaign|victory|candidate|arrest|chase|shooting|senators?\b|\bGOP\b|Lt\. Gov|committee|speaker|\bwins?\b|\bvictory\b", re.I)
MAX_AGE_DAYS = 31
CRIME = re.compile(r"\bpolice\b|shooting|\bshot\b|arrest|murder|homicide|stabbing|\bchase\b|\bgun\b", re.I)
# Sports and game listings ("Irion County vs Water Valley") are never what we want.
SPORTS = re.compile(r"\bvs\.?\b|basketball|football|volleyball|baseball|softball|soccer|varsity|playoffs?|\btournament\b|scoreboard|\bNo\. \d+|\bupset\b|\bseason\b|\bcoach|\bAstros\b|\bTexans\b|\bRockets\b|\bCowboys\b|\bSpurs\b|\bMavericks\b|Longhorns|Aggies|Cougars|Red Raiders|Bears\b|Mustangs|Horned Frogs", re.I)
# Many Texas county names exist in other states (Leon, Floyd, Harris...). Drop stories that name another state.
OTHER_STATES = re.compile(r"\b(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|Tallahassee|Atlanta|Rome News)\b")
# Sources to leave out (finance tickers, aggregators, clickbait). Add names here as you spot them.
SKIP_SOURCES = re.compile(r"tradingview|biggo|shattered\.io|the cool down|finance|stock|marketscreener|newswire|business wire|globe ?newswire|pr newswire|worldatlas|msn|aol|manila times|latham|eb-5", re.I)


def same_story(a, b):
    """Two headlines about the same event share most of their words."""
    wa, wb = (set(re.findall(r"[a-z]{4,}", t.lower())) for t in (a, b))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6
QUERY_TOPICS = '(water OR drought OR power OR grid OR outage OR "data center" OR wildfire OR "burn ban" OR pollution OR environment)'


def get(url, tries=4):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e:  # rate limits or network blips: wait and retry
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def build_outlets(county_names):
    places = collections.defaultdict(set)
    txt = get("https://www2.census.gov/geo/docs/reference/codes2020/place_by_cou/st48_tx_place_by_county2020.txt").decode("utf-8")
    incorporated = collections.defaultdict(set)
    for line in txt.splitlines()[1:]:
        p = line.split("|")
        if len(p) < 8:
            continue
        name = re.sub(r"\s+(city|town|village|CDP)$", "", p[6])
        county = p[3].replace(" County", "")
        places[name.lower()].add(county)
        if p[7] == "INCORPORATED PLACE":
            incorporated[county].add(name)

    wiki = json.loads(get("https://en.wikipedia.org/w/api.php?action=parse&page=List_of_newspapers_in_Texas&prop=wikitext&format=json"))
    text = wiki["parse"]["wikitext"]["*"]
    # only current papers: the first two sections (directory list + papers not in the directory)
    current = re.split(r"==\s*College newspapers\s*==", text)[0]

    def clean(s):
        s = re.sub(r"<ref.*?(</ref>|/>)", "", s, flags=re.S)
        s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
        s = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", s)
        return re.sub(r"''+", "", s).strip()

    outlets = collections.defaultdict(list)
    for table in current.split("{|")[1:]:
        for row in table.split("\n|-")[1:]:
            cells = [c.strip() for c in re.split(r"\n\|", ("\n" + row.strip()).replace("||", "\n|"))][1:]
            if len(cells) < 2:
                continue
            title, city = clean(cells[0]), clean(cells[1]).split(",")[0].strip()
            if not title or title.startswith("}"):
                continue
            for county in places.get(city.lower(), ()):
                if county in county_names and not any(o["name"] == title for o in outlets[county]):
                    outlets[county].append({"name": title, "city": city})
    return {c: sorted(outlets.get(c, []), key=lambda o: o["name"]) for c in county_names}, incorporated


def shared_county_names():
    """Texas county names that other states also use (e.g. Floyd, Leon, Harris)."""
    txt = get("https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt").decode("utf-8", "ignore")
    other = set()
    for line in txt.splitlines()[1:]:
        p = line.split("|")
        if len(p) > 4 and p[0] != "TX":
            other.add(re.sub(r"\s+(County|Parish|Borough|Census Area|city)$", "", p[4]))
    return other


def norm_source(s):
    s = re.sub(r"^the\s+", "", s.lower())
    s = re.sub(r"\s*[|\-–].*$", "", s)  # "The Daily News | Texas' Oldest..." -> "daily news"
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def search(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    root = ET.fromstring(get(url))
    items = []
    for i in root.findall("./channel/item"):
        src = i.find("source")
        source = src.text if src is not None else ""
        title = i.findtext("title") or ""
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)]
        try:
            date = parsedate_to_datetime(i.findtext("pubDate")).date().isoformat()
        except Exception:
            date = ""
        items.append({"title": title, "source": source, "url": i.findtext("link"), "date": date})
    return items


def categorize(title):
    for cat, rx in CAT_RE:
        if rx.search(title):
            return cat
    return None


COMMON_WORDS = {"Center", "Mission", "Commerce", "Industry", "Sunset", "Union", "Liberty", "Victoria", "Garden", "Point", "Grove", "Valley", "Lake", "Rose", "Cross", "Plains", "Energy", "Power", "Data", "Water", "Spring", "Springs", "Hope", "Paris", "Moody", "Price", "Early", "Converse", "Content", "Electra", "Novice", "Edge"}


def texas_context(it, place_words):
    """For county names that other states share: the headline must say Texas or name one of the county's towns
    (as a whole word), or the outlet's own name must include Texas or one of those towns."""
    towns = [w for w in place_words if not w.endswith(" County") and w not in COMMON_WORDS]
    if re.search(r"\bTexas\b|\bTX\b", it["title"]):
        return True
    if towns and re.search(r"\b(" + "|".join(re.escape(w) for w in towns) + r")\b", it["title"]):
        return True
    src_towns = [w for w in towns if len(w) >= 5]
    return bool(re.search(r"texas|\btx\b", it["source"], re.I) or (src_towns and re.search("|".join(re.escape(w) for w in src_towns), it["source"])))


def pick(items, place_words, local_names, limit, per_category=None, strict=False):
    place_rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in place_words) + r")\b") if place_words else None
    cutoff = (datetime.now(timezone.utc).date().toordinal()) - MAX_AGE_DAYS
    seen, keep = set(), []
    for it in items:
        key = re.sub(r"[^a-z0-9]", "", it["title"].lower())[:70]
        if key in seen or SKIP_SOURCES.search(it["source"]) or it["source"].startswith("http"):
            continue
        if re.search(r"\bTexas County\b|, MO\b|Missouri", it["title"] + " " + it["source"]):
            continue  # Texas County is in Missouri
        if SPORTS.search(it["title"]) or CRIME.search(it["title"]) or (OTHER_STATES.search(it["title"] + " " + it["source"]) and "Texas" not in it["title"]):
            continue
        if not it["date"] or datetime.fromisoformat(it["date"]).toordinal() < cutoff:
            continue  # only this month's stories
        cat = categorize(it["title"])
        if not cat or (OFF_TOPIC.search(it["title"]) and cat in ("Power", "Environment")):
            continue
        ns = norm_source(it["source"])
        local = any(ns and (ns in ln or ln in ns) for ln in local_names)
        names_place = bool(place_rx and place_rx.search(it["title"]))
        if not (local or names_place):
            continue
        if strict and not local and not texas_context(it, place_words):
            continue
        seen.add(key)
        keep.append({**it, "category": cat, "local": local})
    # local outlets first, then newest first; then drop repeats of the same event
    keep.sort(key=lambda s: (not s["local"], -int(s["date"].replace("-", ""))))
    unique = []
    for s in keep:
        if not any(same_story(s["title"], u["title"]) for u in unique):
            unique.append(s)
    keep = unique
    if per_category:  # keep a mix of topics
        counts, mixed = collections.Counter(), []
        for s in keep:
            if counts[s["category"]] < per_category:
                mixed.append(s); counts[s["category"]] += 1
        keep = mixed
    return keep[:limit]


def main():
    topo = json.loads((DATA / "tx-counties.json").read_text())
    counties = sorted(g["properties"]["name"].replace(" County", "") for g in topo["objects"]["counties"]["geometries"])
    only = sys.argv[1:]  # optional: run for just some counties, e.g. python3 scripts/fetch_stories.py Travis Hood

    print("Building local outlet list…")
    outlets, towns = build_outlets(set(counties))
    (DATA / "outlets.json").write_text(json.dumps(outlets, indent=1, ensure_ascii=False))
    print(f"  {sum(len(v) for v in outlets.values())} newspapers in {sum(1 for v in outlets.values() if v)} counties")

    shared = shared_county_names()
    out_path = DATA / "stories.json"
    result = json.loads(out_path.read_text()) if (only and out_path.exists()) else {"counties": {}}

    print("Statewide stories…")
    state_items = []
    for q in ['Texas "data center" when:30d', 'Texas (ERCOT OR "power grid" OR outage) when:30d',
              'Texas (drought OR "burn ban" OR wildfire) when:30d', 'Texas (water supply OR aquifer OR reservoir OR "water plan") when:30d',
              'Texas (pollution OR TCEQ OR "air quality" OR emissions) when:30d']:
        state_items += search(q)
        time.sleep(PAUSE)
    result["statewide"] = pick(state_items, ["Texas", "Texans", "ERCOT"], [], 10, per_category=2)

    todo = [c for c in counties if not only or c in only]
    for n, county in enumerate(todo, 1):
        paper_towns = sorted({o["city"] for o in outlets[county]})[:3]
        place_terms = [f'"{county} County"'] + [f'"{t}, Texas"' for t in paper_towns]
        q = f'({" OR ".join(place_terms)}) {QUERY_TOPICS} when:30d'
        try:
            items = search(q)
        except Exception as e:
            print(f"  {county}: search failed ({e}); keeping old stories")
            continue
        place_words = [f"{county} County"] + sorted(towns.get(county, set()) | set(paper_towns), key=len, reverse=True)
        place_words = [w for w in place_words if len(w) > 3]
        local_names = [norm_source(o["name"]) for o in outlets[county]]
        result["counties"][county] = pick(items, place_words, local_names, PER_COUNTY, per_category=3, strict=county in shared)
        print(f"  [{n}/{len(todo)}] {county}: {len(result['counties'][county])} stories")
        time.sleep(PAUSE)

    result["updated"] = datetime.now(timezone.utc).date().isoformat()
    out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print("Done. Wrote", out_path)


if __name__ == "__main__":
    main()
