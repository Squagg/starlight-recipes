"""Build the Chemistry tab's reaction calculator data from Starlight's game files.

  python3 tools/build_reactions.py /path/to/space-station-14

Writes `const CRX=...` into index.html: every chemical reaction outside drinks and food,
with reactants (and which are catalysts), products, temperature limits and mixing method,
plus reagent names, colours and where the basic chemicals come from.
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
from gamedata import load

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")

def dispenser(g):
    """reagents the chem dispenser makes or ships with, from its prototype"""
    ents = g["protos"].get("entity", {})
    out = {}
    for c in (ents.get("ChemDispenserEmpty", {}).get("components") or []):
        if c.get("type") == "ReagentDispenser":
            for k in (c.get("generatableReagents") or {}): out[k] = "chem dispenser"
    def jug_reagent(jid):
        for c in (ents.get(jid, {}).get("components") or []):
            if c.get("type") == "SolutionContainerManager":
                for sol in (c.get("solutions") or {}).values():
                    for r in (sol or {}).get("reagents") or []:
                        if isinstance(r, dict) and r.get("ReagentId"): return r["ReagentId"]
        return re.sub(r"^Jug", "", jid)
    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("id"), str) and x["id"].startswith("Jug"): yield x["id"]
            for v in x.values(): yield from walk(v)
        elif isinstance(x, list):
            for v in x: yield from walk(v)
    for c in (ents.get("ChemDispenser", {}).get("components") or []):
        if c.get("type") == "EntityTableContainerFill":
            for jid in walk(c): out.setdefault(jug_reagent(jid), "chem dispenser jug")
    return out

def main():
    root = sys.argv[1]
    g = load(root)
    reags = g["protos"].get("reagent", {})
    rx = []
    for rid, x in sorted(g["reactions"].items()):
        f = x.get("__file__", "").lower()
        if "/drinks" in f or "/food" in f: continue
        reac = x.get("reactants") or {}
        prods = x.get("products") or {}
        if not prods: continue
        r = {"id": rid,
             "in": [[k, (v.get("amount", 1) if isinstance(v, dict) else v), 1 if isinstance(v, dict) and v.get("catalyst") else 0] for k, v in reac.items()],
             "out": [[k, v] for k, v in prods.items()]}
        if x.get("minTemp"): r["min"] = x["minTemp"]
        if x.get("maxTemp"): r["max"] = x["maxTemp"]
        mix = x.get("requiredMixerCategories") or []
        if mix: r["mix"] = mix
        rx.append(r)
    used = {a[0] for r in rx for a in r["in"]} | {a[0] for r in rx for a in r["out"]}
    names = {k: g["reagent_name"](k) for k in used}
    colors = {k: reags[k]["color"] for k in used if k in reags and isinstance(reags[k].get("color"), str)}
    src = dispenser(g)
    src.update({"Water": "any sink or water tank", "WeldingFuel": "welding fuel tank", "Plasma": "plasma vial (ChemVend, chemistry locker) or ground plasma sheets", "Blood": "draw it with a syringe"})
    data = {"rx": rx, "names": names, "colors": colors, "src": {k: v for k, v in src.items() if k in used}}
    js = "const CRX=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    html = open(PAGE, encoding="utf-8").read()
    if re.search(r"^const CRX=.*$", html, re.M):
        html = re.sub(r"^const CRX=.*$", lambda m: js, html, count=1, flags=re.M)
    else:
        html = html.replace("\nconst CHEM=", "\n" + js + "\nconst CHEM=", 1)
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"{len(rx)} reactions, {len(names)} reagents, {len(data['src'])} with known sources")
    print("sources:", data["src"])

if __name__ == "__main__":
    main()
