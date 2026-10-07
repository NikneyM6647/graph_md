import re
import os
import math
import colorsys
from pathlib import Path

import yaml
import networkx as nx
from pyvis.network import Network

BASE = Path(__file__).resolve().parent
VAULT = BASE / "vault"
LINKS_YAML = BASE / "links.yaml"

WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")

MIN_SIZE = 100                    # 100 байт
MAX_SIZE = 10 * 1024 * 1024       # 10 МБ
LOG_RANGE = math.log(MAX_SIZE / MIN_SIZE)

VAULT.mkdir(exist_ok=True)


def size_to_color(size: int) -> str:
    """Плавный логарифмический градиент синий -> красный."""
    if size <= MIN_SIZE:
        t = 0.0
    elif size >= MAX_SIZE:
        t = 1.0
    else:
        t = math.log(size / MIN_SIZE) / LOG_RANGE

    # hue 210° (синий) -> 0° (красный), через cyan/green/yellow
    hue = (210 - 210 * t) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 1.0)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def parse_md(path: Path):
    raw = path.read_text(encoding="utf-8", errors="ignore")

    title = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = path.stem

    links = [l.strip() for l in WIKILINK_RE.findall(raw)]

    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    return {
        "name": path.stem,
        "path": str(path),
        "title": title,
        "links": links,
        "text": raw,
        "size": size,
    }


def scan_vault():
    if not VAULT.exists():
        return []
    return [parse_md(p) for p in sorted(VAULT.rglob("*.md"))]


def load_links_yaml():
    if not LINKS_YAML.exists():
        return {}
    try:
        data = yaml.safe_load(LINKS_YAML.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}

    out = {}
    for src, targets in data.items():
        if not targets:
            continue
        if not isinstance(targets, list):
            targets = [targets]
        norm = []
        for t in targets:
            if isinstance(t, str):
                norm.append({"target": t, "type": "related", "note": ""})
            elif isinstance(t, dict) and "target" in t:
                norm.append({
                    "target": t["target"],
                    "type": t.get("type", "related"),
                    "note": t.get("note", ""),
                })
        out[src] = norm
    return out


def save_links_yaml(links: dict):
    clean = {}
    for src, targets in links.items():
        if not targets:
            continue
        clean[src] = []
        for t in targets:
            item = {"target": t["target"]}
            if t.get("type") and t["type"] != "related":
                item["type"] = t["type"]
            if t.get("note"):
                item["note"] = t["note"]
            clean[src].append(item)

    LINKS_YAML.write_text(
        yaml.safe_dump(clean, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )


def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def build_graph(records, manual_links):
    by_name = {r["name"]: r for r in records}
    G = nx.DiGraph()

    for r in records:
        color = size_to_color(r["size"])
        G.add_node(
            r["name"],
            label=r["title"][:30],
            title=f"{r['title']}\n{r['name']}\n{human_size(r['size'])}",
            color=color,
        )

    for r in records:
        for target in r["links"]:
            if target in by_name:
                G.add_edge(r["name"], target, type="wiki")
            else:
                for other in records:
                    if other["title"] == target:
                        G.add_edge(r["name"], other["name"], type="wiki")
                        break

    for src, targets in manual_links.items():
        if src not in by_name:
            continue
        for t in targets:
            dst = t["target"]
            if dst in by_name and dst != src:
                G.add_edge(
                    src, dst,
                    type="manual",
                    subtype=t.get("type", "related"),
                    note=t.get("note", ""),
                )
    return G


def render_graph_html(G, height=800):
    net = Network(
        height=f"{height}px",
        width="100%",
        directed=True,
        bgcolor="#1e1e1e",
        font_color="white",
        cdn_resources="in_line",
    )
    net.barnes_hut(spring_length=140)

    for n, data in G.nodes(data=True):
        net.add_node(
            n,
            label=data.get("label", n),
            title=data.get("title", ""),
            size=20,
            color=data.get("color", "#7bd88f"),
        )

    for u, v, d in G.edges(data=True):
        t = d.get("type")
        if t == "wiki":
            net.add_edge(u, v, color="#4ea1ff", width=1.5)
        elif t == "manual":
            subtype = d.get("subtype", "related")
            color = {
                "related": "#7bd88f",
                "parent": "#ff8c42",
                "answer": "#c792ea",
                "contradicts": "#ff5555",
            }.get(subtype, "#7bd88f")
            net.add_edge(u, v, color=color, width=2, title=d.get("note", ""))
        else:
            net.add_edge(u, v, color="#888", width=1)

    return net.generate_html()