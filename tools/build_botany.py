"""Build the Botany view's plant data from Starlight's game files.

  python3 tools/build_botany.py /path/to/space-station-14

Writes `const BOT=...` into index.html: every plant with its chemicals (amount =
min + potency / potencyDivisor, clamped to min..max, as BotanySystem.Produce does),
yield, potency, growth timing, harvest type, what it mutates into, temperature needs
and where to get the seeds. Defaults for fields a plant leaves out come from the
Plant*Component classes.
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
from gamedata import load

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")
# component defaults (Content.Shared/Botany/Components)
DEF = {"potency": 1, "growthStages": 6, "waterConsumption": 0.5, "nutrientConsumption": 0.75,
       "lowHeatTolerance": 283, "highHeatTolerance": 303, "harvestRepeat": "NoRepeat"}

def comps(e):
    return {c["type"]: c for c in (e.get("components") or []) if isinstance(c, dict) and "type" in c}

def main():
    root = sys.argv[1]
    g = load(root)
    ents = g["protos"].get("entity", {})
    loc_name = g["ent_name"]
    # seed sources
    vend = g["protos"].get("vendingMachineInventory", {}).get("MegaSeedServitorInventory", {})
    stock, contra = vend.get("startingInventory") or {}, vend.get("contrabandInventory") or {}
    crates = {}
    for cid, e in ents.items():
        if "/Fills/Crates/" not in e.get("__file__", "") and "Crates" not in e.get("__file__", ""): continue
        for c in comps(e).values():
            for x in re.findall(r"'id': '([A-Za-z0-9]+Seeds)'", str(c)):
                crates.setdefault(x, set()).add(loc_name(cid))
    plants = []
    for pid, e in ents.items():
        if e.get("abstract"): continue
        c = g["ent_comps"](pid)
        if "PlantData" not in c: continue
        pd, pl, gr, at, hv, ch = (c.get(k, {}) for k in ("PlantData", "Plant", "PlantGrowth", "PlantAtmospheric", "PlantHarvest", "PlantChemicals"))
        seed = pd.get("packetPrototype")
        name = g["loc"].get(pd.get("name", ""), "") or e.get("name") or pid
        chems = []
        for rid, q in (ch.get("chemicals") or {}).items():
            q = q or {}
            chems.append([rid, g["reagent_name"](rid), q.get("min", 0), q.get("max", 0), q.get("potencyDivisor", 0)])
        products = pd.get("productPrototypes") or []
        lo, hi = at.get("lowHeatTolerance", DEF["lowHeatTolerance"]), at.get("highHeatTolerance", DEF["highHeatTolerance"])
        plants.append({
            "id": pid, "name": name, "seed": seed,
            "products": [[p, loc_name(p)] for p in products],
            "yield": pl.get("yield", 0), "potency": pl.get("potency", DEF["potency"]),
            "life": pl.get("lifespan", 0), "mature": pl.get("maturation", 0), "prod": pl.get("production", 0),
            "repeat": hv.get("harvestRepeat", DEF["harvestRepeat"]),
            "water": gr.get("waterConsumption", DEF["waterConsumption"]), "food": gr.get("nutrientConsumption", DEF["nutrientConsumption"]),
            "heat": [lo, hi] if (lo, hi) != (DEF["lowHeatTolerance"], DEF["highHeatTolerance"]) else None,
            "chems": chems, "mut": pd.get("mutationPrototypes") or [],
            "vend": stock.get(seed) or 0, "contra": contra.get(seed) or 0,
            "crates": sorted(crates.get(seed, [])),
        })
    # mutation-only plants that reuse their parent's seed packet don't come from the vendor themselves
    parents = {}
    for p in plants:
        for m in p["mut"]: parents.setdefault(m, []).append(p["id"])
    byseed = {}
    for p in plants: byseed.setdefault(p["seed"], []).append(p)
    for p in plants:
        if p["id"] in parents and any(q is not p and q["id"] not in parents for q in byseed[p["seed"]]):
            p["vend"] = p["contra"] = 0; p["crates"] = []
        if p["id"].startswith("Fake"): p["name"] += " (fake)"
    ids = {p["id"] for p in plants}
    for p in plants: p["mut"] = [m for m in p["mut"] if m in ids]
    plants.sort(key=lambda p: p["name"].lower())
    js = "const BOT=" + json.dumps({"plants": plants}, ensure_ascii=False, separators=(",", ":")) + ";"
    html = open(PAGE, encoding="utf-8").read()
    if re.search(r"^const BOT=.*$", html, re.M):
        html = re.sub(r"^const BOT=.*$", lambda m: js, html, count=1, flags=re.M)
    else:
        html = html.replace("\nconst CHEM=", "\n" + js + "\nconst CHEM=", 1)
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"{len(plants)} plants")
    return plants

if __name__ == "__main__":
    ps = main()
    for p in ps[:80]:
        print(f"{p['name'][:22]:22} y{p['yield']} p{p['potency']} m{p['mature']} pr{p['prod']} {p['repeat'][:4]} v{p['vend']}/{p['contra']} {p['crates'][:1]} mut{len(p['mut'])} | " + ", ".join(f"{c[1]} {c[2]}-{c[3]}/{c[4]}" for c in p['chems'])[:90] + f" | {[x[1] for x in p['products']]}")
