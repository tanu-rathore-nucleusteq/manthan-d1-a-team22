"""Extract slide text, tables and speaker notes from a .pptx as Markdown.

Standard library only. Usage:
    python read_pptx.py deck.pptx [--no-notes] [--out deck.md]
"""
import argparse
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
R_ID = "{%s}id" % NS["r"]
NOTES_TYPE = "/notesSlide"
TITLE_TYPES = {"title", "ctrTitle"}


def rels_path(part):
    d, f = posixpath.split(part)
    return posixpath.join(d, "_rels", f + ".rels")


def load_rels(z, part):
    """Map rId -> (type, absolute part path) for a part."""
    path = rels_path(part)
    if path not in z.namelist():
        return {}
    base = posixpath.dirname(part)
    out = {}
    for rel in ET.fromstring(z.read(path)).findall("rel:Relationship", NS):
        if rel.get("TargetMode") == "External":
            continue
        target = posixpath.normpath(posixpath.join(base, rel.get("Target")))
        out[rel.get("Id")] = (rel.get("Type", ""), target.lstrip("/"))
    return out


def para_text(p):
    parts = []
    for n in p.iter():
        if n.tag == "{%s}t" % NS["a"]:
            parts.append(n.text or "")
        elif n.tag == "{%s}br" % NS["a"]:
            parts.append("\n")
    return "".join(parts).strip()


def placeholder_type(sp):
    ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
    return None if ph is None else ph.get("type", "body")


def table_md(tbl):
    rows = []
    for tr in tbl.findall("a:tr", NS):
        cells = []
        for tc in tr.findall("a:tc", NS):
            text = " ".join(t for t in (para_text(p) for p in tc.iter("{%s}p" % NS["a"])) if t)
            cells.append(text.replace("|", "\\|").replace("\n", " "))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def read_slide(z, part):
    root = ET.fromstring(z.read(part))
    title, body, tables, images = None, [], [], 0
    tree = root.find("p:cSld/p:spTree", NS)
    if tree is None:
        return title, body, tables, images
    for el in tree.iter():
        tag = el.tag.split("}")[-1]
        if tag == "pic":
            images += 1
        elif tag == "tbl":
            md = table_md(el)
            if md:
                tables.append(md)
        elif tag == "sp":
            tx = el.find("p:txBody", NS)
            if tx is None:
                continue
            paras = tx.findall("a:p", NS)
            if placeholder_type(el) in TITLE_TYPES and title is None:
                title = " ".join(t for t in map(para_text, paras) if t) or None
                continue
            for p in paras:
                text = para_text(p)
                if not text:
                    continue
                ppr = p.find("a:pPr", NS)
                level = int(ppr.get("lvl", "0")) if ppr is not None else 0
                body.append("  " * level + "- " + text.replace("\n", " "))
    return title, body, tables, images


def read_notes(z, slide_part):
    for rtype, target in load_rels(z, slide_part).values():
        if rtype.endswith(NOTES_TYPE) and target in z.namelist():
            root = ET.fromstring(z.read(target))
            lines = []
            for sp in root.iter("{%s}sp" % NS["p"]):
                if placeholder_type(sp) != "body":
                    continue
                for p in sp.iter("{%s}p" % NS["a"]):
                    t = para_text(p)
                    if t:
                        lines.append(t)
            return "\n".join(lines)
    return ""


def slide_parts(z):
    pres = "ppt/presentation.xml"
    rels = load_rels(z, pres)
    root = ET.fromstring(z.read(pres))
    parts = []
    for sld in root.findall("p:sldIdLst/p:sldId", NS):
        rel = rels.get(sld.get(R_ID))
        if rel and rel[1] in z.namelist():
            parts.append(rel[1])
    return parts


def convert(path, notes=True):
    with zipfile.ZipFile(path) as z:
        parts = slide_parts(z)
        out = [f"# {posixpath.basename(path.replace(chr(92), '/'))}", f"{len(parts)} slides", ""]
        for i, part in enumerate(parts, 1):
            title, body, tables, images = read_slide(z, part)
            out.append(f"## Slide {i}: {title or '(no title)'}")
            out.extend(body)
            for t in tables:
                out += ["", t]
            if images:
                out += ["", f"_[{images} image(s) on this slide; text inside images is not extracted]_"]
            if notes:
                n = read_notes(z, part)
                if n:
                    out += ["", "**Speaker notes:**", n]
            out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pptx")
    ap.add_argument("--no-notes", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not a.pptx.lower().endswith(".pptx"):
        sys.exit("Only .pptx is supported. Save .ppt files as .pptx first.")
    try:
        md = convert(a.pptx, notes=not a.no_notes)
    except (zipfile.BadZipFile, KeyError) as e:
        sys.exit(f"Not a valid .pptx file: {e}")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {a.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(md)


if __name__ == "__main__":
    main()
