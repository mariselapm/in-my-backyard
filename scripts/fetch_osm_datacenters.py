#!/usr/bin/env python3
"""Get the data centers that volunteers have mapped in OpenStreetMap for Texas.

Run it from the project folder:   python3 scripts/fetch_osm_datacenters.py
It writes data/osm-datacenters.json: one entry per site (buildings within about a mile of
each other in the same county), with its county, location, number of buildings and names.

OpenStreetMap data is free to use under the Open Database License. The site must show
"© OpenStreetMap contributors" with a link to https://www.openstreetmap.org/copyright.
The map is made by volunteers, so it is not a complete list. Uses only the Python standard library.
"""
import csv, json, math, collections, subprocess, urllib.error, urllib.request, urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUERY = """[out:json][timeout:120];
area["ISO3166-2"="US-TX"][admin_level=4]->.tx;
(nwr["telecom"="data_center"](area.tx); nwr["building"="data_center"](area.tx); nwr["building"="data_centre"](area.tx); nwr["industrial"="data_center"](area.tx););
out center tags;"""
GROUP_KM = 1.5


def load_counties():
    topo = json.loads((DATA / "tx-counties.json").read_text())
    t = topo.get("transform")
    arcs = []
    for a in topo["arcs"]:
        x = y = 0; pts = []
        for p in a:
            if t:
                x += p[0]; y += p[1]
                pts.append((x * t["scale"][0] + t["translate"][0], y * t["scale"][1] + t["translate"][1]))
            else:
                pts.append(tuple(p))
        arcs.append(pts)
    ring = lambda ids: [pt for i in ids for pt in (arcs[i] if i >= 0 else arcs[~i][::-1])]
    out = []
    for g in topo["objects"]["counties"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        out.append((g["properties"]["name"], [[ring(r) for r in p] for p in polys]))
    return out


def inside(pt, r):
    x, y = pt; c = False; j = len(r) - 1
    for i in range(len(r)):
        (xi, yi), (xj, yj) = r[i], r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def county_of(pt, counties):
    for name, polys in counties:
        for p in polys:
            if inside(pt, p[0]) and not any(inside(pt, h) for h in p[1:]):
                return name.replace(" County", "")
    return None


def main():
    req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                 data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                 headers={"User-Agent": "In My Backyard student news prototype"})
    try:
        raw = urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.URLError:
        # Older Macs' built-in Python can't connect to this server; curl can.
        raw = subprocess.run(["curl", "-sf", "-A", "In My Backyard student news prototype", "--data-urlencode",
                              f"data={QUERY}", "https://overpass-api.de/api/interpreter"],
                             capture_output=True, check=True, timeout=200).stdout
    elements = json.loads(raw)["elements"]
    counties = load_counties()
    sites = []
    for e in elements:
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if c["lat"] is None:
            continue
        tags = e.get("tags", {})
        county = county_of((c["lon"], c["lat"]), counties)
        if not county:
            continue
        label = tags.get("operator") or tags.get("name") or ""
        for s in sites:
            if s["county"] == county and math.hypot((s["lat"] - c["lat"]) * 111, (s["lon"] - c["lon"]) * 95) < GROUP_KM:
                s["buildings"] += 1; s["_names"][label] += 1 if label else 0
                break
        else:
            sites.append({"county": county, "lat": c["lat"], "lon": c["lon"], "buildings": 1,
                          "_names": collections.Counter({label: 1} if label else {})})
    for s in sites:
        s["names"] = [n for n, k in s.pop("_names").most_common() if n and k][:4]
        s["lat"] = round(s["lat"], 5); s["lon"] = round(s["lon"], 5)
    sites.sort(key=lambda s: (s["county"], -s["buildings"]))
    out = {"updated": date.today().isoformat(), "source": "OpenStreetMap contributors (ODbL)", "sites": sites}
    (DATA / "osm-datacenters.json").write_text(json.dumps(out, indent=1))
    # Same list as a spreadsheet the team can paste into the master sheet as its own tab
    with open(DATA / "osm-datacenters.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["county", "names", "buildings", "latitude", "longitude", "source", "retrieved"])
        for s in sites:
            w.writerow([s["county"], "; ".join(s["names"]), s["buildings"], s["lat"], s["lon"], "© OpenStreetMap contributors (ODbL)", out["updated"]])
    print(f"{len(elements)} buildings -> {len(sites)} sites in {len({s['county'] for s in sites})} counties. Wrote data/osm-datacenters.json")


if __name__ == "__main__":
    main()
