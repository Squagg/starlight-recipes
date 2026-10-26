"""Compare the site's recipe data against the current Starlight game files.

  python3 tools/check_game_data.py /path/to/space-station-14 [--apply]

Reports cooking recipes and chemical reactions that were added, removed or changed in the
game since the site's data was built. With --apply, it rewrites those entries in index.html
and stamps today's date as the data date, and rebuilds the Chemistry tab's reaction
calculator and plant list from the same files. Slicing, assembly, vendors and icons are not
covered; the report lists anything that needs a manual look.
"""
import sys, os, re, json, datetime, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from gamedata import load

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")

def site_data(html):
    """pull the R and RX arrays out of the page's data line"""
    out = {}
    for key in ("R", "RX"):
        m = re.search(r"(?:const |,)" + key + r"=(\[)", html)
        i = m.start(1); depth = 0; s = False; esc = False
        for j in range(i, len(html)):
            c = html[j]
            if s:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': s = False
            elif c == '"': s = True
            elif c == "[": depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0: break
        out[key] = (i, j + 1, json.loads(html[i:j + 1]))
    return out

def amt(v):
    return v.get("amount", 1) if isinstance(v, dict) else v

def game_recipe(r, g, old):
    rec = dict(old or {})
    rec.update({"id": r["id"], "result": r["result"], "name": g["ent_name"](r["result"]),
                "device": r.get("deviceType", old.get("device") if old else "Microwave") or "Microwave",
                "time": r.get("time", 5)})
    rec["group"] = r.get("group") or rec.get("group") or "Other"
    if not rec.get("desc") and g["ent_desc"](r["result"]): rec["desc"] = g["ent_desc"](r["result"])
    rec["solids"] = [[g["ent_name"](k), v, k] for k, v in (r.get("solids") or {}).items()]
    rec["reagents"] = [[g["reagent_name"](k), v, k] for k, v in (r.get("reagents") or {}).items()]
    return rec

def game_reaction(x, g, old):
    rx = dict(old or {"drink": False, "mix": "", "temp": None})
    rx.update({"id": x["id"],
               "reagents": [[g["reagent_name"](k), amt(v), k] for k, v in (x.get("reactants") or {}).items()
                            if not (isinstance(v, dict) and v.get("catalyst"))],
               "products": [[g["reagent_name"](k), v, k] for k, v in (x.get("products") or {}).items()],
               "temp": x.get("minTemp") or None})
    rx["name"] = rx["products"][0][0] if rx["products"] else x["id"]
    mix = x.get("requiredMixerCategories") or []
    rx["mix"] = "Shake in a shaker" if "Shake" in mix else "Stir with a spoon" if "Stir" in mix else rx.get("mix", "")
    return rx

def key_r(r): return (r["result"], r.get("device"), r.get("time"), sorted(map(tuple, r["solids"])), sorted(map(tuple, r["reagents"])))
def key_x(x): return (sorted((a[2], a[1]) for a in x["reagents"]), sorted((a[2], a[1]) for a in x["products"]), x.get("temp"))

def main():
    root = sys.argv[1]; apply = "--apply" in sys.argv
    g = load(root)
    # deep fryer recipes turn one item into one fried item; treat them as one-ingredient cooking recipes
    for fid, f in (g["protos"].get("deepFryingRecipe") or {}).items():
        if f.get("ingredient") and f.get("result"):
            g["recipes"][fid] = {"id": fid, "result": f["result"], "time": f.get("time", 5), "group": "Deep fried",
                                 "deviceType": "DeepFryer", "solids": {f["ingredient"]: 1}, "__file__": f.get("__file__", "")}
    # hidden easter-egg recipes stay off the site
    g["recipes"] = {k: v for k, v in g["recipes"].items() if not v.get("secretRecipe") and v.get("group") != "Secret"}
    html = open(PAGE, encoding="utf-8").read()
    sd = site_data(html)
    report = []
    new_lists = {}
    for key, game, conv, cmp, label in (("R", g["recipes"], game_recipe, key_r, "cooking recipe"),
                                         ("RX", g["reactions"], game_reaction, key_x, "reaction")):
        old = {o["id"]: o for o in sd[key][2]}
        if key == "RX":   # only update reactions the site already tracks, plus new drink reactions
            drinkish = {o["id"] for o in sd[key][2]}
            game = {k: v for k, v in game.items() if k in drinkish or "drink" in str(v.get("__file__", "")).lower()}
        out = []
        for oid, o in old.items():
            if key == "R" and o.get("device") == "Mixing":
                # made by mixing reagents: these come from reaction prototypes that spawn an item
                x = g["reactions"].get(oid)
                if not x: report.append(f"REMOVED {label}: {o['name']} ({oid})"); continue
                gr = sorted((k, amt(v)) for k, v in (x.get("reactants") or {}).items())
                if gr != sorted((a[2], a[1]) for a in o["reagents"]): report.append(f"CHANGED mixing recipe: {o['name']} ({oid}) - check by hand")
                out.append(o); continue
            if oid not in game:
                report.append(f"REMOVED {label}: {o['name']} ({oid})"); continue
            n = conv(game[oid], g, o)
            if cmp(n) != cmp(o): report.append(f"CHANGED {label}: {o['name']} ({oid})")
            out.append(n)
        for gid, gx in game.items():
            if gid in old: continue
            if key == "RX" and "drink" not in gx.get("__file__", "").lower(): continue
            n = conv(gx, g, None)
            if key == "RX": n["drink"] = True
            out.append(n); report.append(f"NEW {label}: {n['name']} ({gid}) - needs an icon check")
        new_lists[key] = out
    commit = subprocess.run(["git", "-C", root, "log", "-1", "--format=%h %cs"], capture_output=True, text=True).stdout.strip()
    print(f"Starlight game files at {commit}")
    print("\n".join(report) if report else "No differences in cooking recipes or tracked reactions.")
    if apply and (report or any(new_lists[k] != sd[k][2] for k in sd)):
        spans = sorted(((sd[k][0], sd[k][1], k) for k in sd), reverse=True)
        for i, j, k in spans:
            html = html[:i] + json.dumps(new_lists[k], ensure_ascii=False, separators=(",", ":")) + html[j:]
        html = re.sub(r'const DATA_DATE="[^"]*"', f'const DATA_DATE="{datetime.date.today().isoformat()}"', html)
        open(PAGE, "w", encoding="utf-8").write(html)
        print("Updated index.html")
    if apply:
        import build_reactions
        sys.argv = [sys.argv[0], root]
        build_reactions.main()
        import build_botany
        build_botany.main()

if __name__ == "__main__":
    main()
