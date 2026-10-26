"""Add missing item icons to sprite.png for every recipe item that has none yet.

  python3 tools/add_icons.py /path/to/space-station-14

Needs the item textures checked out (Resources/Textures/...); in a sparse clone, add the
.rsi folders this script reports as missing and rerun. Icons are 32x32 cells in a
32-column sheet; new ones go into free cells, adding rows when the sheet is full.
"""
import sys, os, re, json
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from gamedata import load
from check_game_data import site_data

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE, SHEET = os.path.join(HERE, "index.html"), os.path.join(HERE, "sprite.png")

def sprite_of(g, eid):
    c = g["ent_comps"](eid).get("Sprite", {})
    rsi, state = c.get("sprite"), c.get("state")
    if not state:
        for L in c.get("layers") or []:
            if isinstance(L, dict) and L.get("state"):
                state, rsi = L["state"], L.get("sprite", rsi); break
    return rsi, state

def main():
    root = sys.argv[1]
    g = load(root)
    html = open(PAGE, encoding="utf-8").read()
    m = re.search(r"const IC=(\{[^}]*\})", html)
    IC = json.loads(m.group(1))
    sd = site_data(html)
    want = []
    for r in sd["R"][2]:
        for e in [r["result"]] + [x[2] for x in r["solids"]]:
            if "e:" + e not in IC and e not in want: want.append(e)
    sheet = Image.open(SHEET).convert("RGBA")
    used = {tuple(v) for v in IC.values()}
    def free_cells():
        rows = sheet.height // 32
        for y in range(rows):
            for x in range(32):
                if (x, y) not in used: yield x, y
    added, missing = 0, []
    for e in want:
        if e.startswith("Mob"): continue   # live animals: their sprites are layered bodies, not item icons
        rsi, state = sprite_of(g, e)
        if not rsi or not state: continue
        png = os.path.join(root, "Resources/Textures", rsi, state + ".png")
        if not os.path.exists(png):
            missing.append(os.path.join("Resources/Textures", rsi)); continue
        img = Image.open(png).convert("RGBA")
        meta = json.load(open(os.path.join(root, "Resources/Textures", rsi, "meta.json")))
        w, h = meta.get("size", {}).get("x", 32), meta.get("size", {}).get("y", 32)
        frame = img.crop((0, 0, w, h)).resize((32, 32), Image.NEAREST)
        cell = next(free_cells(), None)
        if cell is None:
            grown = Image.new("RGBA", (sheet.width, sheet.height + 64))
            grown.paste(sheet, (0, 0)); sheet = grown
            cell = next(free_cells())
        sheet.paste(frame, (cell[0] * 32, cell[1] * 32))
        used.add(cell); IC["e:" + e] = list(cell); added += 1
    sheet.save(SHEET, optimize=True)
    html = html[:m.start(1)] + json.dumps(IC, separators=(", ", ": ")) + html[m.end(1):]
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"added {added} icons; sheet is now {sheet.width}x{sheet.height}")
    if missing: print("check out these textures and rerun:", sorted(set(missing)))

if __name__ == "__main__":
    main()
