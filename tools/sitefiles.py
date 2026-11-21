"""Where the site's files live, cache-busting for them, and the sitemap.

index.html loads data.js and sprite.png with ?v=<hash>; _headers lets browsers keep
both for a year, so the hash must change whenever either file does. Every tool that
writes them calls stamp() at the end, which also rebuilds sitemap.xml and robots.txt.
"""
import os, re, json, hashlib, unicodedata
from xml.sax.saxutils import escape
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")
DATA = os.path.join(HERE, "data.js")
SHEET = os.path.join(HERE, "sprite.png")
SITE = "https://starlight-recipes.pages.dev"
# tabs and chemistry views that have their own address (see TAB_T in index.html)
VIEWS = ["drinks", "chem", "chem/gold", "chem/calc", "chem/labels", "chem/botany", "chem/machinechems",
         "chem/plumbing", "chem/notes", "combos", "menus", "list"]

def load_data():
    out = {}
    for line in open(DATA, encoding="utf-8"):
        if not line.startswith("const "): continue
        for part in re.split(r",(?=[A-Z_]{1,9}=)", line[6:].rstrip().rstrip(";")):
            k, v = part.split("=", 1)
            out[k] = json.loads(v)
    return out

def slug(s):
    """same as slug() in index.html"""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not ("̀" <= c <= "ͯ"))
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s))

def item_paths(d):
    """recipe and drink addresses, deduplicated in the same order as BYSLUG in index.html"""
    items = [r["name"] for r in d["R"]] + [p["outputs"][0][0] for p in d["P"]] + [q["name"] for q in d["SQ"]]
    drinks = [x["name"] for x in d["RX"] if x.get("drink")]
    out = []
    for tab, names in (("recipes", items), ("drinks", drinks)):
        seen = set()
        for n in names:
            s, k = slug(n) or "item", 2
            while s in seen: s = slug(n) + "-" + str(k); k += 1
            seen.add(s); out.append(f"{tab}/{s}")
    return out

def sitemap():
    d = load_data()
    day = d.get("DATA_DATE", "")
    urls = [""] + VIEWS + item_paths(d)
    body = "".join(f"<url><loc>{escape(SITE + '/' + u)}</loc>{f'<lastmod>{day}</lastmod>' if day else ''}</url>\n" for u in urls)
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nDisallow: /tools/\nDisallow: /data/\nSitemap: {SITE}/sitemap.xml\n")
    return len(urls)

def stamp():
    html = open(PAGE, encoding="utf-8").read()
    for name, path in (("data.js", DATA), ("sprite.png", SHEET)):
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:10]
        html = re.sub(re.escape(name) + r"\?v=[0-9a-z]+", f"{name}?v={h}", html)
    open(PAGE, "w", encoding="utf-8").write(html)
    sitemap()

if __name__ == "__main__":
    stamp()
    print(sitemap(), "addresses in sitemap.xml")
