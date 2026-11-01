"""Where the site's files live, and cache-busting for them.

index.html loads data.js and sprite.png with ?v=<hash>; _headers lets browsers keep
both for a year, so the hash must change whenever either file does. Every tool that
writes them calls stamp() at the end.
"""
import os, re, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")
DATA = os.path.join(HERE, "data.js")
SHEET = os.path.join(HERE, "sprite.png")

def stamp():
    html = open(PAGE, encoding="utf-8").read()
    for name, path in (("data.js", DATA), ("sprite.png", SHEET)):
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:10]
        html = re.sub(re.escape(name) + r"\?v=[0-9a-z]+", f"{name}?v={h}", html)
    open(PAGE, "w", encoding="utf-8").write(html)
