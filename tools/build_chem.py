"""Turn the "SS14 Chemistry for Kobolds" sheet export into the Chemistry tab's data.

  python3 tools/build_chem.py            # rewrites the CHEM line in index.html

Source: data/chemistry-for-kobolds.txt, an export of
https://docs.google.com/spreadsheets/d/1ExvhhgdQMwxDBjOEoU6wGEOixlurMb_ECHWumff4kIU
with each tab as "## Sheet name: X" followed by its rows as CSV. Re-export the sheet to
that file and rerun this script to pick up changes.
"""
import csv, io, json, re, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "data", "chemistry-for-kobolds.txt")
PAGE = os.path.join(HERE, "index.html")

def sheets(text):
    out, name, buf = {}, None, []
    for line in text.split("\n"):
        m = re.match(r"^## Sheet name: (.+)$", line)
        if m:
            if name: out[name] = list(csv.reader(io.StringIO("\n".join(buf))))
            name, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if name: out[name] = list(csv.reader(io.StringIO("\n".join(buf))))
    return out

COLOR = re.compile(r"\[color=#?([0-9a-fA-F]{6}|white)\]")
def is_header(s):
    return bool(re.match(r"^[^\w\[(]{4,}", s)) or s in ("MOOD CHEMICALS",) or s.endswith(" SECTOR")
def header_name(s):
    return re.sub(r"^[^\w]+|[^\w]+$", "", s).strip().title() if s not in ("MOOD CHEMICALS",) else "Mood chemicals"
def prefix(s): return s[0] if s and s[0] in ",;:.`^*~" else ""
def color(s):
    m = COLOR.search(s)
    return None if not m else ("ffffff" if m.group(1) == "white" else m.group(1).lower())
def key(s):
    s = COLOR.sub("", s).replace("[bold]", "")
    s = s.lstrip(",;:.`^*~").split("|")[0].strip()
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

def labels(rows):
    names = ["Category", "Colored", "Patch", "Meme", "OwO", "OwO (worse)"]
    lists = {n: [] for n in names}
    blocks = {}
    extra = {}
    cur = {i: names[i - 1] for i in range(1, 7)}
    for r in rows[1:]:
        r = (r + [""] * 7)[:7]
        c0 = r[0]
        if "hand_labeler_saved_labels" in c0:
            # the block follows a caption row like "COLORED LABELS"
            pass
        for i in range(1, 7):
            v = r[i].strip()
            if not v: continue
            if v.endswith(" SECTOR"):
                cur[i] = v.title(); extra[cur[i]] = []; continue
            target = lists.get(cur[i], extra.get(cur[i]))
            if v.startswith("hand_labeler_saved_labels") or v.startswith(",,,,,,,,,,AIR,,,,,,,,,,\\n"):
                continue
            target.append({"h": header_name(v)} if is_header(v) else {"t": v})
    # ready-made config blocks from column 0 (caption row, then the block)
    cap = None
    for r in rows[1:]:
        c0 = (r[0] if r else "").strip()
        m = re.match(r"^(CATEGORY|COLORED|MEME|OWO) LABELS$", c0)
        if m: cap = {"CATEGORY": "Category", "COLORED": "Colored", "MEME": "Meme", "OWO": "OwO"}[m.group(1)]; continue
        if cap and "\\n" in c0:
            body = re.sub(r'^hand_labeler_saved_labels = "+|"+$', "", c0)
            blocks.setdefault(cap, body)   # first (quoted) version wins
            cap = None
    types = [{"id": n, "items": lists[n], "block": blocks.get(n)} for n in names]
    types += [{"id": n, "items": v, "block": None} for n, v in extra.items()]
    howto = [(r[0] if r else "").strip() for r in rows[1:32]]
    return types, [h for h in howto if h and "hand_labeler" not in h and "\\n" not in h]

def guide(rows, kind):
    """rows -> intro text, sections of steps"""
    sections, intro = [], {}
    for r in rows:
        r = (r + [""] * 6)[:6]
        a, b, c, d, e = (x.strip() for x in r[:5])
        if not any((a, b, c, d, e)) or a == "What you're making": continue
        if not sections and (len(a) > 120 or len(c) > 120 or (not a and not b)):
            # free-text intro rows before the first section
            for x in (a, c, d):
                if len(x) > 40: intro.setdefault("texts", []).append(x)
            continue
        if a and not b and c and (d.endswith("jugs") or d.endswith("jugs total") or (a.isupper() and "|" not in a) or a in ("Cryos",)) and "|" not in a:
            sections.append({"title": a, "desc": c, "total": d, "rows": []}); continue
        if not sections: continue
        row = {"name": a, "how": c, "total": d}
        if kind == "silver":
            row["method"] = b
            if "|" in a: row["cat"] = a
            if e: row["label"] = e
        else:
            row["temp"] = b
            if e: row["label"] = e
        if not a and sections[-1]["rows"]:
            sections[-1]["rows"].append({**row, "cont": True})
        else:
            sections[-1]["rows"].append(row)
    return intro, sections

def by_key(items, p, k, any_prefix=False):
    """same category symbol and chem abbreviation (AMOX, NECR/NECRO...)"""
    for exact in (True, False):
        for s in items:
            ks = key(s)
            if (any_prefix or prefix(s) == p) and ks and k and (ks == k if exact else (len(k) >= 3 and len(ks) >= 3 and (ks.startswith(k) or k.startswith(ks)))):
                return s
    return None

def blocks(rows, side_col=None, always=False, split_on=()):
    """free-form sheet tab -> paragraphs and tables. side_col: a column used for margin notes,
    pulled out into a separate tips list when the row has nothing else in the middle columns"""
    out, tips, table = [], [], None
    def end():
        nonlocal table
        if table:
            keep = [i for i in range(max(map(len, table))) if any(i < len(r) and r[i].strip() for r in table)]
            t = [[(r[i].strip() if i < len(r) else "") for i in keep] for r in table]
            head = any(re.match(r"^(Why\?|Usecase|Chems Made|Grinder|Examine Text.*|Initial Chemicals.*|What's a reductive mixture\?)$", c) for c in t[0])
            out.append({"table": t, "head": head})
        table = None
    for r in rows:
        r = [x for x in r]
        if side_col is not None and len(r) > side_col and r[side_col].strip() and (always or not any(x.strip() for x in r[1:side_col])):
            tips.append(r[side_col].strip()); r = r[:side_col]
        cells = [x.strip() for x in r]
        filled = [x for x in cells if x]
        if not filled:
            end(); continue
        if len(filled) == 1 and cells[0]:
            end()
            t = cells[0]
            out.append({"p": t, "mono": bool(re.search(r"[├┼┤┴]", t)), "h": t.isupper() and len(t) < 40 and bool(re.search("[A-Z]", t))})
            continue
        if table is not None and cells[0] in split_on: end()
        if table is None: table = []
        table.append(cells)
    end()
    return out, " ".join(tips)

def map_labels(types, ident, label=None):
    """find the label for one chem in every label set. ident is any label for that chem; the
    chem is identified by its category symbol and abbreviation, and joke label sets (which
    have no abbreviation) are matched through the colored label's colour"""
    out = {}
    p, k = prefix(ident), key(ident)
    sets = {t["id"]: [x["t"] for x in t["items"] if "t" in x] for t in types}
    colored = label if label in sets["Colored"] and key(label) == k else by_key(sets["Colored"], p, k)
    col = color(colored) if colored else color(ident)
    for t in types:
        tid, items = t["id"], sets[t["id"]]
        if tid in ("Patch", "OwO (worse)"): continue
        if tid in ("Meme", "OwO"):
            hit = next((s for s in items if prefix(s) == p and col and color(s) == col), None)
        else:
            hit = by_key(items, p, k, any_prefix=tid.endswith("Sector"))
        if tid == "Colored": hit = colored
        if hit: out[tid] = hit
    if "Colored" not in out and label and label != ident:
        out = {**map_labels(types, label, label), **out}
    return out

def main():
    sh = sheets(open(SRC, encoding="utf-8").read())
    types, howto = labels(sh["Labels"])
    s_intro, s_secs = guide(sh["ChemistyGuide"], "silver")
    g_intro, g_secs = guide(sh["GoldBeakerGuide"], "gold")
    for secs in (s_secs, g_secs):
        for sec in secs:
            for r in sec["rows"]:
                # the chemistry guide's own colour column is off by a row in places, so it is
                # identified by its category label; the gold guide's label column is reliable
                ident = r.get("cat") or r.get("label")
                if ident: r["labels"] = map_labels(types, ident, r.get("label"))
    extra = {}
    for name, title, side, always, split in (("Botany", "Botany", 7, False, ("Plant",)), ("MachineChems", "Machine chems", None, False, ()),
                                             ("Plumbing", "Plumbing", 3, True, ()), ("Notes", "Notes", None, False, ())):
        if name in sh:
            b, tips = blocks(sh[name], side, always, split)
            extra[name.lower()] = {"title": title, "blocks": b, "tips": tips}
    chem = {"extra": extra, "types": [{"id": t["id"], "items": t["items"], "block": t["block"]} for t in types],
            "howto": howto, "silver": {"intro": s_intro.get("texts", []), "sections": s_secs},
            "gold": {"intro": g_intro.get("texts", []), "sections": g_secs}}
    js = "const CHEM=" + json.dumps(chem, ensure_ascii=False, separators=(",", ":")) + ";"
    html = open(PAGE, encoding="utf-8").read()
    if re.search(r"^const CHEM=.*$", html, re.M):
        html = re.sub(r"^const CHEM=.*$", lambda m: js, html, count=1, flags=re.M)
    else:
        html = html.replace("\nconst $=i=>", "\n" + js + "\nconst $=i=>", 1)
    open(PAGE, "w", encoding="utf-8").write(html)
    print(f"label sets: {', '.join(t['id'] + ' ' + str(sum('t' in x for x in t['items'])) for t in types)}")
    for n, secs in (("silver", s_secs), ("gold", g_secs)):
        print(n, [(s["title"], len(s["rows"])) for s in secs])
    return chem

if __name__ == "__main__":
    c = main()
    json.dump(c, open("/tmp/claude-0/-home-claude/3d09f2ba-9756-5d4b-af6e-a1893d260942/scratchpad/chem.json", "w"), ensure_ascii=False, indent=1)
