# Notes Graph

**A lightweight desktop app for visualizing links between Markdown notes.**

An alternative to Obsidian's graph view — no browser, no database, just files.



## Features

- 📝 Notes — plain `.md` files in `vault/`
- 🔗 Links — automatic via `[[wiki-links]]` + manual via UI
- 🕸 Interactive graph — zoom, drag, hover
- 🎨 Node color = file size (log gradient: blue → red)
- 🪟 Native window (PySide6) — no browser
- 💾 No database — text files only
- 🔀 Git-friendly

## Install & Run

```bash
https://github.com/NikneyM6647/Graph_md.git
cd notes-graph
pip install -r requirements.txt
python main.py
```

Structure
notes-graph/
├── main.py
├── core.py
├── requirements.txt
├── links.yaml
├── vault/          # your .md notes
└── docs/
    └── screenshot.png


Link types
Type	Color
related	🟢 green
parent	🟠 orange
answer	🟣 purple
contradicts	🔴 red
[[wiki]]	🔵 blue

Node colors
File size → log gradient from 🔵 blue (≤100 B) to 🔴 red (≥10 MB).

Tech
Python 3.10+ · PySide6 · QWebEngineView · pyvis + vis.js · NetworkX · PyYAML


























