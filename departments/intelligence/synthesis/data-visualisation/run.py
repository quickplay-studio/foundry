"""Data Visualisation: GitHub implementation of departments/intelligence/synthesis/data-visualisation/SKILL.md.

Picks charts from the validate sidecars by data shape, draws each as a plain SVG string (no plotting library, Okabe-Ito
colours, direct labels, a marker per signal), checks every number in a title against the chart data, writes the data
beside each chart and fills the charts block in report.md. The model only proposes titles and labels, never numbers.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import intelkit as I  # noqa: E402
from foundry import jobkit as k  # noqa: E402

BLUE, ORANGE, GREEN, RED, INK, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#1a1a1a", "#595959"
SIGNAL = {"pass": (GREEN, "circle"), "warn": (ORANGE, "triangle"), "fail": (RED, "square")}
START, END = "<!-- charts:start -->", "<!-- charts:end -->"
MAX_CHARTS, MIN_POINTS = 5, 3


def svg(title, desc, h, body, w=700):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" font-family="Arial, sans-serif" font-size="13">'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc><rect width="{w}" height="{h}" fill="#ffffff"/>'
            f'<text x="16" y="26" font-size="16" font-weight="bold" fill="{INK}">{esc(title)}</text>{body}</svg>')


def fmt(v):
    return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"


def bar(title, desc, labels, values, log=False, unit=""):
    """Horizontal bars with the value written at the end of each bar. log=True scales by powers of ten for funnels."""
    top = max(values) or 1
    low = min(v for v in values if v > 0) if log and any(v > 0 for v in values) else 1
    scale = lambda v: (0.08 + 0.92 * (math.log10(max(v, low)) - math.log10(low) + 1) / (math.log10(top) - math.log10(low) + 1)) if log else v / top  # noqa: E731
    rows = "".join(f'<text x="200" y="{52 + i * 34 + 15}" text-anchor="end" fill="{INK}">{esc(l[:30])}</text><rect x="208" y="{52 + i * 34}" width="{max(2, 270 * scale(v)):.0f}" height="22" fill="{BLUE}"/>'
                   f'<text x="{214 + max(2, 270 * scale(v)):.0f}" y="{52 + i * 34 + 16}" fill="{INK}">{fmt(v)} {esc(unit)}</text>' for i, (l, v) in enumerate(zip(labels, values)))
    note = f'<text x="16" y="{52 + len(values) * 34 + 8}" font-size="11" fill="{GREY}">Bar length is logarithmic: each step up is about ten times larger.</text>' if log else ""
    return svg(title, desc, 70 + len(values) * 34 + (14 if log else 0), rows + note)


def line(title, desc, labels, values, unit=""):
    lo, hi, w, h = min(values), max(values), 560, 220
    span = (hi - lo) or 1
    pts = [(60 + i * w / (len(values) - 1), 50 + h - (v - lo) / span * h) for i, v in enumerate(values)]
    marks = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.5" fill="{BLUE}"/>' for x, y in pts)
    ends = "".join(f'<text x="{x:.0f}" y="{y - 9:.0f}" text-anchor="middle" fill="{INK}">{fmt(values[i])}</text>' for i, (x, y) in [(0, pts[0]), (len(pts) - 1, pts[-1])])
    axis = (f'<line x1="60" y1="{50 + h}" x2="{60 + w}" y2="{50 + h}" stroke="{GREY}"/><text x="56" y="{54 + h}" text-anchor="end" fill="{GREY}">{fmt(lo)}</text><text x="56" y="58" text-anchor="end" fill="{GREY}">{fmt(hi)}</text>'
            f'<text x="60" y="{72 + h}" fill="{GREY}">{esc(labels[0])}</text><text x="{60 + w}" y="{72 + h}" text-anchor="end" fill="{GREY}">{esc(labels[-1])}</text><text x="16" y="{h + 94}" font-size="11" fill="{GREY}">{esc(unit)}</text>')
    return svg(title, desc, h + 104, f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="none" stroke="{BLUE}" stroke-width="2.5"/>' + marks + ends + axis)


def scorecard(title, desc, labels, signals):
    out = ""
    for i, (job, sig) in enumerate(zip(labels, signals)):
        colour, shape = SIGNAL.get(sig, (GREY, "circle"))
        y, mark = 54 + i * 32, ""
        mark = (f'<circle cx="224" cy="{y + 8}" r="8" fill="{colour}"/>' if shape == "circle" else f'<polygon points="224,{y} 233,{y + 16} 215,{y + 16}" fill="{colour}"/>' if shape == "triangle"
                else f'<rect x="216" y="{y}" width="16" height="16" fill="{colour}"/>')
        out += f'<text x="200" y="{y + 13}" text-anchor="end" fill="{INK}">{esc(job)}</text>{mark}<text x="244" y="{y + 13}" font-weight="bold" fill="{INK}">{esc(sig)}</text>'
    return svg(title, desc, 70 + len(labels) * 32, out)


def numbers_ok(title, allowed):
    """Every number in a title must exist in the chart data (commas ignored)."""
    words = "zero one two three four five six seven eight nine ten eleven twelve".split()
    title = " ".join(str(words.index(w.lower())) if w.lower() in words else w for w in title.split())  # spelt-out numbers count too
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", title) if n.replace(",", "").rstrip(".")]
    return all(any(abs(n - a) <= 0.006 + abs(a) * 0.0005 for a in allowed) for n in nums)


def candidates(ctx):
    out = []
    v, vert, comp, price, tam = (I.dct(k.read(ctx, f"validate/{n}.json")) for n in ("verdict", "vertical-analysis", "competitor-teardown", "pricing-research", "tam-market-sizing"))
    sig = I.dct(v.get("signals"))
    if sig:
        n = {s: list(sig.values()).count(s) for s in SIGNAL}
        out.append(dict(name="scorecard", type="scorecard", labels=list(sig), values=[{"pass": 2, "warn": 1, "fail": 0}.get(s, 0) for s in sig.values()], signals=list(sig.values()), key="verdict.json signals", src=v, measure="Signal", unit="pass, warn or fail",
                        extra=list(n.values()) + [len(sig)], finding=f"{n['pass']} of {len(sig)} jobs pass, {n['warn']} warn, {n['fail']} fail"))
    plans = [p for p in map(I.dct, I.lst(price.get("plans"))) if I.num(p.get("gbp_month")) and p.get("period") != "one-off"]
    if plans:
        vals = [float(p["gbp_month"]) for p in plans]
        out.append(dict(name="competitor-prices", type="bar", labels=[f"{p.get('competitor')} {p.get('plan')}" for p in plans], values=vals, key="pricing-research.json plans", src=price, measure="Plan price", unit="pounds a month",
                        extra=list(I.quartiles(vals).values()), finding=f"Median plan costs {I.quartiles(vals)['median']:.2f} pounds a month"))
    tr = [t for t in map(I.dct, I.lst(vert.get("trend"))) if I.num(t.get("value")) is not None]
    if tr:
        vals = [float(t["value"]) for t in tr]
        out.append(dict(name="demand-trend", type="line", labels=[str(t.get("month")) for t in tr], values=vals, key="vertical-analysis.json trend", src=vert, measure="Demand", unit=str(vert.get("trend_source", "")),
                        extra=[], finding=f"Demand moved from {fmt(vals[0])} to {fmt(vals[-1])} over the year"))
    if all(I.num(tam.get(x)) for x in ("tam", "sam")) and I.num(I.dct(tam.get("som")).get("base")):
        vals = [float(tam["tam"]), float(tam["sam"]), float(tam["som"]["base"])]
        out.append(dict(name="tam-funnel", type="funnel", labels=["TAM", "SAM", "SOM base, year one"], values=vals, key="tam-market-sizing.json tam, sam, som", src=tam, measure="Revenue", unit="pounds a year", extra=[], finding=f"Base year-one revenue is {fmt(vals[2])} pounds"))
    gaps = [g for g in map(I.dct, I.lst(comp.get("gaps"))) if I.num(g.get("evidence_count"))]
    if gaps:
        out.append(dict(name="complaint-themes", type="bar", labels=[str(g.get("theme")) for g in gaps], values=[float(g["evidence_count"]) for g in gaps], key="competitor-teardown.json gaps", src=comp, measure="Complaints", unit="items", extra=[],
                        finding=f"{gaps[0].get('theme')} is the top complaint with {int(gaps[0]['evidence_count'])} items"))
    for f in sorted((ctx["folder"] / "research" / "data").glob("*"))[:3]:
        try:
            rows = list(csv.reader(f.open(encoding="utf-8"))) if f.suffix == ".csv" else None
            data = [(r[0], float(r[1])) for r in rows[1:] if len(r) > 1 and I.num(r[1]) is not None] if rows else [(str(a), float(b)) for a, b in (json.loads(f.read_text(encoding="utf-8")).items() if f.suffix == ".json" else [])]
        except (OSError, ValueError, AttributeError, TypeError):
            continue
        if data:
            out.append(dict(name="adhoc-" + re.sub(r"[^a-z0-9]+", "-", f.stem.lower()), type="bar", labels=[a for a, _ in data], values=[b for _, b in data], key=f"research/data/{f.name}", src={}, measure=f.stem, unit="", extra=[], finding=""))
    return out


def main(ctx):
    cands, skipped = candidates(ctx), []
    keep = [c for c in cands if len(c["values"]) >= MIN_POINTS]
    skipped = [f"{c['name']}: only {len(c['values'])} points, needs {MIN_POINTS}" for c in cands if len(c["values"]) < MIN_POINTS]
    if not keep:
        return {"skipped": "no sidecar holds a series of 3 or more points to chart: " + ("; ".join(skipped) or "no validate sidecars yet")}
    spec = I.dct(k.ask('Propose titles for these charts. Each title states the finding in under 12 words and contains no numbers you were not given. Return JSON only: {"charts": [{"name": "<as given>", "title": "<finding>", "x_label": "<text>", "y_label": "<text>"}]}\n\n'
                       + "\n".join(f"- {c['name']} ({c['type']}): {c['measure']} by item, {c['unit']}; items: {', '.join(map(str, c['labels'][:8]))}" for c in keep)))
    by_name = {I.txt(s.get("name"), 40): s for s in map(I.dct, I.lst(spec.get("charts")))}
    drawn, blocks = [], []
    for c in keep[:MAX_CHARTS]:
        allowed = c["values"] + c["extra"]
        title = I.txt(by_name.get(c["name"], {}).get("title"), 100)
        plain = f"{c['measure']} by item, {c['unit']}".strip(", ")
        if not (title and len(title.split()) < 12 and numbers_ok(title, allowed)):
            title = c["finding"] if c["finding"] and len(c["finding"].split()) < 12 and numbers_ok(c["finding"], allowed) else plain
        desc = f"{c['type']} chart of {c['measure'].lower()}: " + "; ".join(f"{l} {fmt(v)}" for l, v in list(zip(c["labels"], c["values"]))[:10])
        if c["type"] == "scorecard":
            art = scorecard(title, desc, c["labels"], c["signals"])
        elif c["type"] == "line":
            art = line(title, desc, c["labels"], c["values"], c["unit"])
        else:
            art = bar(title, desc, c["labels"], c["values"], c["type"] == "funnel", c["unit"])
        srcs = [u for u in I.lst(I.dct(c["src"]).get("sources")) if isinstance(u, str)][:5]
        k.write(ctx, f"validate/charts/{c['name']}.svg", art)
        k.write(ctx, f"validate/charts/{c['name']}.json", {"name": c["name"], "type": c["type"], "title": title, "labels": c["labels"], "values": c["values"], "unit": c["unit"], "sidecar_key": c["key"], "sources": srcs,
                                                          "x_label": I.txt(by_name.get(c["name"], {}).get("x_label"), 60), "y_label": I.txt(by_name.get(c["name"], {}).get("y_label"), 60)})
        shown = c["signals"] if c["type"] == "scorecard" else [fmt(v) for v in c["values"]]
        blocks += [f"![{title}](charts/{c['name']}.svg)", "", f"Source: {c['key']}." + (" " + " ".join(srcs[:2]) if srcs else ""), "", *I.table(["Item", "Value"], list(zip(c["labels"][:15], shown[:15]))), ""]
        drawn.append(c["name"])
    skipped += [f"{c['name']}: over the {MAX_CHARTS} chart limit" for c in keep[MAX_CHARTS:]]
    report = k.read(ctx, "validate/report.md")
    embedded = False
    if report and START in report and END in report and report.index(START) < report.index(END):
        head, rest = report.split(START, 1)
        _, tail = rest.split(END, 1)
        new = head + START + "\n" + "\n".join(blocks) + "\n" + END + tail
        if new.splitlines()[0] == report.splitlines()[0]:  # line 1 is never touched
            k.write(ctx, "validate/report.md", new)
            embedded = True
    note = "" if embedded else " Report charts block not filled: " + ("report.md missing" if not report else "markers missing") + "."
    return {"summary": f"Drew {len(drawn)} charts ({', '.join(drawn)}); skipped {len(skipped)}: {'; '.join(skipped)[:120]}.{note}", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
