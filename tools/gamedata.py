"""Load Starlight SS14 prototypes (recipes, reactions, entity and reagent names).

Usage: from gamedata import load; g = load("/path/to/space-station-14")
Handles custom YAML tags (!type:..., !PartialOnly) and Starlight's partial prototypes,
which patch fields onto a prototype defined elsewhere.
"""
import os, re, glob, yaml

class L(yaml.SafeLoader): pass
def _tag(loader, suffix, node):
    if isinstance(node, yaml.MappingNode): return loader.construct_mapping(node, deep=True)
    if isinstance(node, yaml.SequenceNode): return loader.construct_sequence(node, deep=True)
    v = loader.construct_scalar(node)
    return {"__partial__": v} if suffix == "PartialOnly" else v
L.add_multi_constructor("!", _tag)

def _docs(root):
    for f in sorted(glob.glob(os.path.join(root, "Resources/Prototypes/**/*.yml"), recursive=True)):
        try:
            d = yaml.load(open(f, encoding="utf-8"), Loader=L)
        except Exception:
            continue
        if isinstance(d, list):
            for x in d:
                if isinstance(x, dict) and "type" in x: yield f, x

def _ftl(root):
    """locale key -> text, for reagent names and entity name overrides"""
    out = {}
    for f in glob.glob(os.path.join(root, "Resources/Locale/en-US/**/*.ftl"), recursive=True):
        for line in open(f, encoding="utf-8"):
            m = re.match(r"^([\w.-]+)\s*=\s*(.+?)\s*$", line)
            if m: out[m.group(1)] = m.group(2)
    return out

def load(root):
    protos, partials = {}, []
    for f, x in _docs(root):
        t = x["type"]
        if isinstance(t, dict) and "__partial__" in t:
            if isinstance(x.get("id"), str): partials.append((t["__partial__"], x))
            continue
        if not isinstance(t, str) or not isinstance(x.get("id"), str): continue
        x["__file__"] = f
        protos.setdefault(t, {})[x["id"]] = x   # later files override earlier ones
    for t, x in partials:
        base = protos.get(t, {}).get(x["id"])
        if base is not None and isinstance(x.get("id"), str):
            base.update({k: v for k, v in x.items() if k not in ("type", "id")})
    loc = _ftl(root)
    ents = protos.get("entity", {})
    def ent_field(eid, key, seen=None):
        seen = seen or set()
        e = ents.get(eid)
        if not e or eid in seen: return None
        if key in e: return e[key]
        ps = e.get("parent")
        for p in ([ps] if isinstance(ps, str) else ps or []):
            v = ent_field(p, key, seen | {eid})
            if v is not None: return v
        return None
    def ent_name(eid):
        n = loc.get(f"ent-{eid}") or ent_field(eid, "name") or eid
        return loc.get(n, n) if re.match(r"^[\w-]+$", str(n)) and "-" in str(n) else n
    reags = protos.get("reagent", {})
    def reagent_name(rid):
        r = reags.get(rid, {})
        k = r.get("name")
        n = loc.get(k, k) if k else rid
        return re.sub(r"^reagent-name-", "", n).replace("-", " ") if n.startswith("reagent-name-") else n
    def ent_desc(eid):
        d = loc.get(f"ent-{eid}.desc") or ent_field(eid, "description") or ""
        return loc.get(d, d) if re.match(r"^[\w-]+$", str(d)) and "-" in str(d) else d
    def ent_comps(eid, seen=None):
        """components with parent inheritance applied: parents first, child fields win"""
        seen = seen or set()
        e = ents.get(eid)
        if not e or eid in seen: return {}
        out = {}
        ps = e.get("parent")
        for p in ([ps] if isinstance(ps, str) else ps or []):
            for t, c in ent_comps(p, seen | {eid}).items():
                out.setdefault(t, {}).update(c)
        for c in e.get("components") or []:
            if isinstance(c, dict) and "type" in c:
                out.setdefault(c["type"], {}).update(c)
        return out
    return {"protos": protos, "loc": loc, "ent_comps": ent_comps, "ent_name": ent_name, "ent_desc": ent_desc, "reagent_name": reagent_name,
            "recipes": protos.get("microwaveMealRecipe", {}), "reactions": protos.get("reaction", {})}
