#!/usr/bin/env python3
"""Build the animated, theme-aware SVGs for the github.com/mrzroot profile README.

Everything is self-hosted: text is converted to outlines (HarfBuzz + fontTools, so
Persian shapes correctly and nothing depends on the viewer's fonts) and live numbers
come from the GitHub REST API. Run daily by .github/workflows/profile-cards.yml.

    pip install uharfbuzz fonttools && python scripts/build_profile.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import math
import random
import urllib.request
import zlib
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "gen"
USER = "mrzroot"
PARTICLES = json.loads((HERE / "particles.json").read_text())

FLAGSHIPS = [
    ("mihanstack", "MihanStack", "میهن‌استک", "LOCAL API EMULATOR",
     "Local cloud for Iranian payment and SMS APIs: Zarinpal, Zibal, Kavenegar and SMS.ir with failure scenarios, chaos mode and record/replay."),
    ("dibs", "dibs", "", "AI CODING-AGENT SAFETY",
     "Stops Claude Code, Codex, Cursor, Gemini CLI, Copilot and aider from reverting the edits you make by hand. Zero dependencies."),
    ("hamyad", "hamyad", "هم‌یاد", "SHARED MEMORY FOR EVERY AI",
     "One project brain for ChatGPT, Claude, Codex, Gemini, Grok, Cursor, Copilot and more: sessions, decisions and diffs, over MCP and REST."),
    ("dokhaneh", "dokhaneh", "دوخانه", "RELEASE DISTRIBUTION",
     "Publishes every release to GitHub and Iranian hosts with an Ed25519-signed manifest and a verifying fallback installer."),
    ("paknevis", "paknevis", "پاک‌نویس", "PERSIAN TEXT TOOLING",
     "Persian text linter and auto-fixer: half-spaces, Arabic letters, punctuation, digits. CLI, pre-commit and GitHub Action."),
    ("netdoctor-ir", "netdoctor-ir", "", "NETWORK DIAGNOSTICS",
     "Connectivity doctor for developers in Iran: scans 38 dev services, ranks DNS resolvers, switches pip, npm and Docker mirrors."),
    ("flowpilot", "flowpilot", "", "WORKFLOW AUTOMATION",
     "Self-hosted, code-first workflow engine: YAML in Git, cron, webhook and RSS triggers, Telegram steps, Jalali dates."),
    ("sabr", "sabr", "صبر", "RESUMABLE DOWNLOADS",
     "Resumable git clone, docker pull and downloads for links that keep dropping: a drop costs one step, not the whole transfer."),
    ("marz", "marz", "مرز", "GEO-BLOCK & SANCTIONS CHECK",
     "Will your app work in Iran, China and Russia? Scans code for blocked and sanctioned services, with OONI data and fixes."),
]

# Other public repositories: name, description, language, homepage and fork status all come from the API.
MORE = ["agentforge", "awesome-persian-developer-resources", "universal-video-downloader", "page-smash", "jenkins", "printbridge"]
FORK_OF = {"printbridge": "AnouarSbia/printbridge"}   # parent shown on the card; the API list endpoint does not return it

THEMES = {
    # Persian turquoise (Sheikh Lotfollah tile) + amber gold on midnight indigo
    "dark": dict(bg="#070b1a", surface="#0e1428", line="#1a2240", line2="#28325a", text="#eceff7", text2="#a9b1cc",
                 text3="#8089a8", accent="#3fd0c9", gold="#e8b04b", hot="#f0be5e", glow="#3fd0c9", glowA=0.13,
                 dot="#c9d3ff", dotA=0.06, heat=["#121a33", "#0f4a4f", "#16807d", "#25b3ab", "#3fd0c9"]),
    # ivory paper + deep turquoise + burnished gold (all text >= 4.5:1)
    "light": dict(bg="#f7f5ef", surface="#ffffff", line="#e6e2d6", line2="#d6d1c2", text="#0b1230", text2="#3a4363",
                  text3="#5b6383", accent="#0a7671", gold="#8a5c0c", hot="#b7801f", glow="#1fb5ad", glowA=0.16,
                  dot="#0b1230", dotA=0.07, heat=["#ece8dc", "#bfe9e5", "#7fd6cf", "#2fb8af", "#0a7671"]),
}
LANG_COLORS = {"Go": "#00ADD8", "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Groovy": "#4298b8",
               "HTML": "#e34c26", "Shell": "#89e051", "CSS": "#563d7c", "PHP": "#4F5D95"}


# --------------------------------------------------------------------------- text → outlines
GLYPHS: dict = {}   # (font id, glyph name) -> (svg id, path in font units); reset per SVG
F_IDS: list = []
class Font:
    def __init__(self, file: str):
        data = (HERE / "fonts" / file).read_bytes()
        self.tt = TTFont(HERE / "fonts" / file)
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob(data)))
        self.id = "abcdefghij"[len(F_IDS)]
        F_IDS.append(self.id)

    def shape(self, s: str):
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, s: str, size: float, ls: float = 0) -> float:
        _, pos = self.shape(s)
        return sum(p.x_advance for p in pos) * size / self.upem + ls * max(0, len(pos) - 1)

    def glyph(self, name: str) -> str:
        key = (self.id, name)
        if key not in GLYPHS:
            pen = SVGPathPen(self.gs, ntos=lambda v: str(round(v)))
            self.gs[name].draw(pen)
            GLYPHS[key] = (f"{self.id}{len(GLYPHS)}", pen.getCommands())
        return GLYPHS[key][0]

    def use(self, s: str, size: float, x: float, y: float, anchor: str = "start", ls: float = 0) -> str:
        infos, pos = self.shape(s)
        k = size / self.upem
        w = self.width(s, size, ls)
        x0 = x - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
        parts, cx = [], 0.0
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            if self.gs[name].width and name not in ("space", "uni200C", "uni00A0"):
                gid = self.glyph(name)
                oy = f' y="{-p.y_offset}"' if p.y_offset else ""
                parts.append(f'<use href="#{gid}" x="{round(cx + p.x_offset)}"{oy}/>')
            elif name not in ("space", "uni200C", "uni00A0"):
                gid = self.glyph(name)
                parts.append(f'<use href="#{gid}" x="{round(cx + p.x_offset)}"/>')
            cx += p.x_advance + ls / k
        return f'<g transform="translate({x0:.1f} {y:.1f}) scale({k:.5f} {-k:.5f})">' + "".join(parts) + "</g>"


F = {n: Font(f) for n, f in {
    "inter": "Inter-400.ttf", "inter6": "Inter-600.ttf", "mono": "JBMono-400.ttf", "mono6": "JBMono-600.ttf",
    "fa": "Vazir-400.ttf", "fa8": "Vazir-800.ttf", "serif": "Serif-Italic.ttf"}.items()}


def T(font: str, s: str, size: float, x: float, y: float, fill: str, anchor: str = "start", ls: float = 0,
      cls: str = "", extra: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<g{c} fill="{fill}"{extra}>' + F[font].use(s, size, x, y, anchor, ls) + "</g>"


def wrap(font: str, s: str, size: float, width: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if F[font].width(t, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def faNum(v) -> str:
    return str(v).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


# --------------------------------------------------------------------------- GitHub data
def gh(path: str):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception:
        return None


def contributions():
    """Real contribution calendar (GraphQL). Returns None on any failure so nothing is ever invented."""
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        return None
    q = ("query($u:String!){user(login:$u){contributionsCollection{totalCommitContributions totalIssueContributions "
         "totalPullRequestContributions totalPullRequestReviewContributions contributionCalendar{totalContributions "
         "weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}")
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q, "variables": {"u": USER}}).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "User-Agent": USER})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            c = json.load(r)["data"]["user"]["contributionsCollection"]
        cal = c["contributionCalendar"]
        return dict(total=cal["totalContributions"], weeks=[w["contributionDays"] for w in cal["weeks"]],
                    commits=c["totalCommitContributions"], prs=c["totalPullRequestContributions"],
                    issues=c["totalIssueContributions"], reviews=c["totalPullRequestReviewContributions"])
    except Exception as e:   # noqa: BLE001
        print("contributions unavailable:", e)
        return None


def fetch():
    user = gh(f"/users/{USER}") or {}
    repos = gh(f"/users/{USER}/repos?per_page=100&type=owner") or []
    info = {}
    for slug, *_ in FLAGSHIPS:
        r = next((x for x in repos if x["name"] == slug), None) or gh(f"/repos/{USER}/{slug}") or {}
        rel = gh(f"/repos/{USER}/{slug}/releases/latest") or {}
        info[slug] = dict(stars=r.get("stargazers_count", 0), forks=r.get("forks_count", 0),
                          lang=r.get("language") or "", tag=rel.get("tag_name", ""),
                          date=(rel.get("published_at") or "")[:10])
    own = [r for r in repos if not r.get("fork")]
    langs = {}
    for r in own:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    more = {}
    for slug in MORE:
        r = next((x for x in repos if x["name"] == slug), None) or gh(f"/repos/{USER}/{slug}")
        if not r:
            continue
        lang = r.get("language") or ""
        if not lang:   # fall back to the top language by bytes, if GitHub detected any
            ls = gh(f"/repos/{USER}/{slug}/languages") or {}
            lang = max(ls, key=ls.get) if ls else ""
        more[slug] = dict(desc=r.get("description") or "", lang=lang, home=r.get("homepage") or "", fork=bool(r.get("fork")))
    site = next((x for x in repos if x["name"] == f"{USER}.github.io"), {})
    return dict(user=user, repos=repos, own=own, info=info, langs=langs, more=more, cal=contributions(), site=site)


# --------------------------------------------------------------------------- shared SVG bits
def frame(w, h, t, body, extra_css="", rx=22, glow=(0.75, 0.45)):
    gx, gy = glow
    gdefs = "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLYPHS.values())
    GLYPHS.clear()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<defs>
<radialGradient id="g" cx="{gx}" cy="{gy}" r="0.6"><stop offset="0" stop-color="{t['glow']}" stop-opacity="{t['glowA']}"/><stop offset="1" stop-color="{t['glow']}" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{t['dot']}" fill-opacity="{t['dotA']}"/></pattern>
<clipPath id="clip"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>
{gdefs}
</defs>
<style>
.p{{animation:pin 2.4s cubic-bezier(.22,1,.36,1) var(--d) both,tw 3.2s ease-in-out calc(var(--d) + 2.4s) infinite alternate}}
@keyframes pin{{from{{transform:translate(var(--x),var(--y));opacity:0}}}}
@keyframes tw{{to{{opacity:.35}}}}
.fu{{animation:fu 1.1s cubic-bezier(.22,1,.36,1) var(--d,0s) both}}
@keyframes fu{{from{{opacity:0;transform:translateY(14px)}}}}
.h{{fill:{t['hot']}}}.blink{{animation:bl 1.1s steps(1) infinite}}@keyframes bl{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
{extra_css}
</style>
<g clip-path="url(#clip)">
<rect width="{w}" height="{h}" fill="{t['bg']}"/>
<rect width="{w}" height="{h}" fill="url(#dots)"/>
<rect width="{w}" height="{h}" fill="url(#g)"/>
{body}
</g>
<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{rx}" fill="none" stroke="{t['line2']}"/>
</svg>'''


def particles(pts, x, y, w, h, t, rng, rmin=1.1, rmax=2.4, spread=260, d0=0.0, dspan=1.4):
    out = []
    for i, (nx, ny) in enumerate(pts):
        px, py = x + nx * w, y + ny * h
        r = rmin + rng.random() * (rmax - rmin)
        hot = rng.random() < 0.12
        dx, dy = (rng.random() - 0.5) * spread * 2, (rng.random() - 0.5) * spread * 1.4
        d = d0 + rng.random() * dspan
        cls = "p h" if hot else "p"
        out.append(f'<circle class="{cls}" cx="{px:.0f}" cy="{py:.0f}" r="{r:.1f}" style="--x:{dx:.0f}px;--y:{dy:.0f}px;--d:{d:.1f}s"/>')
    return f'<g fill="{t["accent"]}" fill-opacity=".85">' + "".join(out) + "</g>"


def star_path(cx, cy, r, fill):
    import math
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        ang = -math.pi / 2 + k * math.pi / 5
        pts.append(f"{cx + rr*math.cos(ang):.1f},{cy + rr*math.sin(ang):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def dust(n, w, h, t, rng):
    out = []
    for _ in range(n):
        out.append(f'<circle cx="{rng.random()*w:.0f}" cy="{rng.random()*h:.0f}" r="{0.6+rng.random()*1.1:.1f}" fill="{t["text3"]}" fill-opacity="{0.15+rng.random()*0.3:.2f}"/>')
    return "\n".join(out)


# --------------------------------------------------------------------------- header
def header(t, theme):
    rng = random.Random(1405)
    W, H = 1280, 400
    css = ".pd{animation:dr 9s ease-in-out infinite alternate}@keyframes dr{to{transform:translate(-14px,8px)}}"
    pts = PARTICLES["mrz"][:950]
    body = [f'<g class="pd">{dust(90, W, H, t, rng)}</g>',
            particles(pts, 690, 50, 560, 280, t, rng, 1.0, 2.3, 300)]
    a, x = t["accent"], 64
    body.append(f'<g class="fu" style="--d:.1s">'
                f'<rect x="{x}" y="64" width="78" height="26" rx="6" fill="{a}" fill-opacity=".1" stroke="{a}" stroke-opacity=".35"/>'
                + T("mono6", "M-R-Z", 12, x + 39, 82, a, "middle", 1.6)
                + f'<rect x="{x+92}" y="77" width="26" height="1" fill="{t["line2"]}"/>'
                + T("mono", "DEVELOPER TOOLS · PYTHON & TYPESCRIPT · MASHHAD, IRAN", 12, x + 130, 82, t["text2"], ls=1.3) + "</g>")
    body.append(f'<g class="fu" style="--d:.25s">' + T("inter6", "Mohammadreza Zare", 56, x - 3, 160, t["text"], ls=-2.2) + "</g>")
    body.append(f'<g class="fu" style="--d:.4s">' + T("serif", "open-source tools for AI coding agents", 40, x, 212, a) + "</g>")
    body.append(f'<g class="fu" style="--d:.5s">' + T("serif", "and developers in Iran.", 40, x, 254, a) + "</g>")
    body.append(f'<g class="fu" style="--d:.65s">' + T("fa", "ابزارهای متن‌باز برای ایجنت‌های هوش مصنوعی و برنامه‌نویس‌های ایرانی", 19, x, 300, t["text2"]) + "</g>")
    body.append(f'<g class="fu" style="--d:.8s">' + T("mono", "$ open https://mrzroot.github.io", 15, x, 350, t["text3"])
                + f'<rect class="blink" x="{x + F["mono"].width("$ open https://mrzroot.github.io", 15) + 6}" y="338" width="9" height="16" fill="{a}"/></g>')
    body.append(T("mono", "move along · it's particles all the way down", 10.5, 970, 372, t["text3"], "middle", 1.2, extra=' fill-opacity=".8"'))
    return frame(W, H, t, "\n".join(body), css, glow=(0.76, 0.45))


# --------------------------------------------------------------------------- cards
def card(i, spec, info, t, theme):
    slug, name, fa, cat, pitch = spec
    rng = random.Random(zlib.crc32(slug.encode()) % 10000 + (0 if theme == "dark" else 7))
    W, H = 640, 300
    a = t["accent"]
    css = (".gl{animation:br 6s ease-in-out 2.6s infinite alternate;transform-origin:150px 150px}"
           "@keyframes br{to{transform:scale(1.035)}}")
    body = [f'<rect x="16" y="16" width="268" height="268" rx="16" fill="{t["glow"]}" fill-opacity="{t["glowA"]*0.5:.3f}" stroke="{t["line"]}"/>',
            f'<g class="gl">{particles(PARTICLES[slug], 40, 40, 220, 220, t, rng, 1.0, 2.2, 180, 0, 1.0)}</g>']
    for (cx, cy, sx, sy) in [(26, 26, 1, 1), (274, 26, -1, 1), (26, 274, 1, -1), (274, 274, -1, -1)]:
        body.append(f'<path d="M{cx} {cy+12*sy}V{cy}H{cx+12*sx}" fill="none" stroke="{t['gold']}" stroke-width="1.5" stroke-opacity=".8"/>')
    x = 312
    body.append(f'<g class="fu" style="--d:.15s">' + T("mono6", f"{i+1:02d}", 11, x, 48, t["gold"], ls=1.2)
                + T("mono", f"/ {len(FLAGSHIPS):02d} · {cat}", 11, x + 22, 48, t["text3"], ls=1.2) + "</g>")
    body.append(f'<g class="fu" style="--d:.3s">' + T("serif", name, 46, x - 2, 102, t["text"]) + "</g>")
    if fa:
        body.append(f'<g class="fu" style="--d:.4s">' + T("fa8", fa, 18, 612, 98, t["text3"], "end") + "</g>")
    for k, line in enumerate(wrap("inter", pitch, 14.5, 296)[:4]):
        body.append(f'<g class="fu" style="--d:{.45 + k*.06:.2f}s">' + T("inter", line, 14.5, x, 138 + k * 22, t["text2"]) + "</g>")
    # footer chips
    y, cxp = 252, x
    chips = [("star", t["text"]), (info["tag"] or "release", t["text2"]), (info["lang"] or "", t["text2"])]
    for txt, col in chips:
        if not txt:
            continue
        label = str(info["stars"]) if txt == "star" else txt
        w = F["mono"].width(label, 12, .3) + (34 if txt in ("star", info["lang"]) else 22)
        body.append(f'<rect x="{cxp}" y="{y-17}" width="{w:.0f}" height="26" rx="13" fill="{t["dot"]}" fill-opacity=".05" stroke="{t["line2"]}"/>')
        if txt == "star":
            body.append(star_path(cxp + 14, y - 4, 5.5, t["gold"]))
            body.append(T("mono6", label, 12, cxp + 24, y, col, ls=.3))
        elif txt == info["lang"]:
            body.append(f'<circle cx="{cxp+14}" cy="{y-4}" r="4" fill="{LANG_COLORS.get(txt, a)}"/>')
            body.append(T("mono", txt, 12, cxp + 24, y, col, ls=.3))
        else:
            body.append(T("mono", txt, 12, cxp + 11, y, col, ls=.3))
        cxp += w + 8
    return frame(W, H, t, "\n".join(body), css, rx=18, glow=(0.2, 0.5))


# --------------------------------------------------------------------------- stats
def stats(data, t, theme):
    W, H = 1280, 250
    a = t["accent"]
    info, own, langs, user = data["info"], data["own"], data["langs"], data["user"]
    fstars = sum(v["stars"] for v in info.values())
    allstars = sum(r.get("stargazers_count", 0) for r in own)
    rel = sum(1 for v in info.values() if v["tag"])
    cells = [(str(fstars), "flagship stars", "ستاره‌ی پروژه‌های شاخص"),
             (str(len(own)), "original repositories", "مخزن اصلی"),
             (f"{rel}/{len(FLAGSHIPS)}", "with releases", "شاخص با نسخه"),
             (str(allstars), "stars, all repos", "همه‌ی ستاره‌ها")]
    body = [T("mono", "LIVE FROM GITHUB", 11, 48, 52, t["gold"], ls=1.6),
            T("mono", f"updated {dt.date.today().isoformat()} · self-hosted SVG, built daily by a GitHub Action", 11, 196, 52, t["text3"], ls=.4),
            T("fa", "به‌روزرسانی خودکار روزانه", 12, 1232, 52, t["text3"], "end")]
    cw = (W - 96) / 4
    for k, (v, en, fa) in enumerate(cells):
        x = 48 + k * cw
        body.append(f'<g class="fu" style="--d:{.1 + k*.12:.2f}s">'
                    f'<rect x="{x:.0f}" y="74" width="{cw-16:.0f}" height="104" rx="14" fill="{t["dot"]}" fill-opacity=".03" stroke="{t["line"]}"/>'
                    + T("inter6", v, 44, x + 20, 128, t["text"], ls=-1.5)
                    + T("inter", en, 13, x + 20, 158, t["text2"])
                    + T("fa", fa, 12, x + cw - 36, 158, t["text3"], "end") + "</g>")
    # language bar
    total = sum(langs.values()) or 1
    x, y, bw = 48, 206, W - 96
    items = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    body.append(f'<rect x="{x}" y="{y}" width="{bw}" height="8" rx="4" fill="{t["line"]}"/>')
    cx = x
    for k, (lang, n) in enumerate(items):
        w = bw * n / total
        body.append(f'<rect x="{cx:.1f}" y="{y}" width="{max(w-3,2):.1f}" height="8" rx="4" fill="{LANG_COLORS.get(lang, a)}">'
                    f'<animate attributeName="width" from="0" to="{max(w-3,2):.1f}" dur="1.2s" begin="{.3+k*.1:.1f}s" fill="freeze" calcMode="spline" keySplines=".22 1 .36 1"/></rect>')
        cx += w
    lx = x
    for lang, n in items:
        label = f"{lang} {round(100*n/total)}%"
        body.append(f'<circle cx="{lx+4}" cy="{y+28}" r="4" fill="{LANG_COLORS.get(lang, a)}"/>' + T("mono", label, 11, lx + 14, y + 32, t["text2"]))
        lx += F["mono"].width(label, 11) + 36
    return frame(W, H, t, "\n".join(body), "", glow=(0.5, 0.0))


# --------------------------------------------------------------------------- terminal
def terminal(data, t, theme):
    W, H = 1280, 380
    a = t["accent"]
    fs, lh, x0, y0 = 15, 27, 40, 92
    cwid = F["mono"].width("m", fs)
    stars = sum(v["stars"] for v in data["info"].values())
    script = [
        ("cmd", "whoami"),
        ("out", "Mohammadreza Zare (M-R-Z) · Python & TypeScript · Mashhad, Iran"),
        ("cmd", "ls ~/flagships"),
        ("acc", "mihanstack  dibs  hamyad  dokhaneh  paknevis  netdoctor-ir  flowpilot  sabr  marz"),
        ("cmd", "dibs status --oneline"),
        ("out", f"dibs: 0 reverted · your edits are safe · {stars} star{'' if stars == 1 else 's'} across flagships"),
        ("cmd", "echo $SALAM"),
        ("fa", "سلام، خوش آمدید؛ برای همکاری در تلگرام پیام بدهید"),
    ]
    period = 18.0
    body = [f'<rect x="0" y="0" width="{W}" height="44" fill="{t["dot"]}" fill-opacity=".03"/>',
            f'<rect x="0" y="44" width="{W}" height="1" fill="{t["line"]}"/>']
    for k, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        body.append(f'<circle cx="{28+k*20}" cy="22" r="6" fill="{c}" fill-opacity=".85"/>')
    body.append(T("mono", "mrz@mrzroot: ~", 12, W / 2, 27, t["text3"], "middle"))
    body.append(T("mono", "interactive version: mrzroot.github.io/#shell", 11, W - 28, 27, t["text3"], "end"))
    tcur = 0.6
    defs = []
    for n, (kind, text) in enumerate(script):
        y = y0 + n * lh
        if kind == "cmd":
            prompt = "~ $ "
            body.append(T("mono6", prompt, fs, x0, y, a))
            px = x0 + F["mono6"].width(prompt, fs)
            chars = len(text)
            dur = chars * 0.06
            b0, b1 = tcur / period, (tcur + dur) / period
            vals = ";".join(f"{j*cwid:.1f}" for j in range(chars + 1))
            steps = ";".join(f"{(b0 + (b1-b0)*j/chars):.4f}" for j in range(chars + 1))
            defs.append(f'<clipPath id="c{n}"><rect x="{px}" y="{y-fs}" height="{fs+8}" width="0">'
                        f'<animate attributeName="width" values="0;{vals};{chars*cwid:.1f};0" keyTimes="0;{steps};0.97;1" dur="{period}s" repeatCount="indefinite" calcMode="discrete"/></rect></clipPath>')
            body.append(f'<g clip-path="url(#c{n})">' + T("mono", text, fs, px, y, t["text"]) + "</g>")
            tcur += dur + 0.35
        else:
            b = tcur / period
            font, col, anchor, xx = ("fa", t["text2"], "start", x0) if kind == "fa" else ("mono", a if kind == "acc" else t["text2"], "start", x0)
            g = T(font, text, fs + (1 if kind == "fa" else 0), xx, y, col, anchor)
            body.append(f'<g opacity="0">{g}<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{b:.4f};{b+0.001:.4f};0.97;1" dur="{period}s" repeatCount="indefinite"/></g>')
            tcur += 0.5
    yb = y0 + len(script) * lh
    body.append(T("mono6", "~ $ ", fs, x0, yb, a))
    body.append(f'<rect class="blink" x="{x0 + F["mono6"].width("~ $ ", fs) + 2:.1f}" y="{yb-fs+2}" width="{cwid:.1f}" height="{fs+2}" fill="{a}"/>')
    return frame(W, H, t, "<defs>" + "".join(defs) + "</defs>\n" + "\n".join(body), "", rx=16, glow=(0.85, 1.0))


# --------------------------------------------------------------------------- shared helpers (new)
def clean(s: str, font: str = "inter") -> str:
    """Drop emoji/symbols the outlined font has no glyph for, collapse whitespace."""
    cmap = F[font].tt.getBestCmap()
    return " ".join("".join(ch for ch in s if ord(ch) in cmap).split())


def nice_date(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return f"{d.day} {d.strftime('%b')} {d.year}"
    except ValueError:
        return ""


def chip(body, x, y, label, t, font="mono", color=None, dot=None, star=False):
    """Pill used in card footers; returns the next x."""
    w = F[font].width(label, 12, .3) + (34 if (dot or star) else 22)
    body.append(f'<rect x="{x}" y="{y-17}" width="{w:.0f}" height="26" rx="13" fill="{t["dot"]}" fill-opacity=".05" stroke="{t["line2"]}"/>')
    off = 11
    if dot:
        body.append(f'<circle cx="{x+14}" cy="{y-4}" r="4" fill="{dot}"/>')
        off = 24
    if star:
        body.append(star_path(x + 14, y - 4, 5.5, t["gold"]))
        off = 24
    body.append(T(font, label, 12, x + off, y, color or t["text2"], ls=.3))
    return x + w + 8


# --------------------------------------------------------------------------- activity (replaces the sparse snake grid)
def activity(data, t, theme):
    c = data.get("cal")
    if not c:
        return None
    W, H = 1280, 404
    a, heat = t["accent"], t["heat"]
    weeks = [w for w in c["weeks"] if w]
    first = next((i for i, w in enumerate(weeks) if any(d["contributionCount"] for d in w)), len(weeks) - 12)
    n = max(20, min(26, len(weeks) - first))          # zoom on the period that has data; never pad with fake days
    win = weeks[-n:]
    pitch = min(30.0, 600.0 / n)
    cell = pitch - 5
    gx, gy = 48 + 40, 142
    LV = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    total_win = sum(d["contributionCount"] for w in win for d in w)
    d0, d1 = win[0][0]["date"], win[-1][-1]["date"]
    body = [T("mono", "ACTIVITY", 11, 48, 52, t["gold"], ls=1.6),
            T("mono", f"real GitHub data · self-hosted SVG · updated {dt.date.today().isoformat()}", 11, 128, 52, t["text3"], ls=.4),
            T("fa", "فعالیت واقعی از گیت‌هاب", 12, 1232, 52, t["text3"], "end")]
    body.append(T("inter6", str(c["total"]), 46, 46, 112, t["text"], ls=-1.5))
    bw = F["inter6"].width(str(c["total"]), 46, -1.5)
    body.append(T("inter", "contributions in the last 12 months", 14, 46 + bw + 14, 112, t["text2"]))
    # weekday labels (GitHub weeks start on Sunday)
    for r, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body.append(T("mono", lab, 10, gx - 10, gy + r * pitch + cell * .72, t["text3"], "end"))
    last_month = None
    for i, w in enumerate(win):
        x = gx + i * pitch
        m = w[0]["date"][:7]
        if m != last_month and (i == 0 or w[0]["date"][8:10] <= "14" or i == 0):
            if last_month is not None or i == 0:
                body.append(T("mono", dt.date.fromisoformat(w[0]["date"]).strftime("%b"), 10, x, gy - 12, t["text3"]))
            last_month = m
        col = []
        for d in w:
            r = d["weekday"]
            lv = LV.get(d["contributionLevel"], 0)
            cx, cy = x, gy + r * pitch
            extra = f' stroke="{t["gold"]}" stroke-width="1.6"' if d["date"] == dt.date.today().isoformat() else ""
            col.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="{cell*.22:.1f}" fill="{heat[lv]}"{extra}>'
                       f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')
        body.append(f'<g class="fu" style="--d:{.05 + i*.035:.2f}s">' + "".join(col) + "</g>")
    ly = gy + 7 * pitch + 16
    body.append(T("mono", f"last {n} weeks · {nice_date(d0)} to {nice_date(d1)}", 11, 48, ly + 9, t["text3"], ls=.2))
    # legend, right-aligned to the end of the grid
    lx = gx + n * pitch - 5 * 16 - 38
    body.append(T("mono", "less", 10, lx - 8, ly + 9, t["text3"], "end"))
    for k in range(5):
        body.append(f'<rect x="{lx + k*16}" y="{ly}" width="11" height="11" rx="2.5" fill="{heat[k]}"/>')
    body.append(T("mono", "more", 10, lx + 5 * 16 + 4, ly + 9, t["text3"]))

    # right column: breakdown + latest releases
    rx, rw = 720, 512
    tiles = [(c["commits"], "commits"), (c["prs"], "pull requests"), (c["issues"], "issues")]
    tw = (rw - 2 * 12) / 3
    for k, (v, lab) in enumerate(tiles):
        x = rx + k * (tw + 12)
        body.append(f'<g class="fu" style="--d:{.1 + k*.1:.2f}s"><rect x="{x:.0f}" y="82" width="{tw:.0f}" height="72" rx="14" fill="{t["dot"]}" fill-opacity=".03" stroke="{t["line"]}"/>'
                    + T("inter6", str(v), 30, x + 18, 124, t["text"], ls=-1) + T("inter", lab, 12.5, x + 18, 143, t["text2"]) + "</g>")
    body.append(T("mono", "LATEST RELEASES", 11, rx, 192, t["gold"], ls=1.6))
    body.append(T("mono", "from the Releases API", 10.5, rx + rw, 192, t["text3"], "end", .3))
    rels = sorted(((v["date"], k, v["tag"]) for k, v in data["info"].items() if v["tag"] and v["date"]), reverse=True)[:5]
    y = 224
    if rels:
        body.append(f'<rect x="{rx+5.5}" y="{y-6}" width="1" height="{(len(rels)-1)*30+2}" fill="{t["line2"]}"/>')
    for k, (date, slug, tag) in enumerate(rels):
        yy = y + k * 30
        body.append(f'<g class="fu" style="--d:{.3 + k*.08:.2f}s"><circle cx="{rx+6}" cy="{yy-5}" r="{5 if k == 0 else 4}" fill="{t["gold"] if k == 0 else a}"/>'
                    + T("inter6", slug, 14.5, rx + 24, yy, t["text"])
                    + T("mono", tag, 12, rx + 24 + F["inter6"].width(slug, 14.5) + 12, yy, a, ls=.3)
                    + T("mono", nice_date(date), 12, rx + rw, yy, t["text3"], "end") + "</g>")
    return frame(W, H, t, "\n".join(body), "", glow=(0.85, 0.1))


# --------------------------------------------------------------------------- portfolio card (10th tile)
def star_points(n_edge=14):
    pts = []
    v = [(0.5 + 0.44 * math.sin(k * math.pi / 4), 0.5 - 0.44 * math.cos(k * math.pi / 4)) for k in range(8)]
    for k in range(8):
        (x0, y0), (x1, y1) = v[k], v[(k + 3) % 8]
        pts += [(x0 + (x1 - x0) * i / n_edge, y0 + (y1 - y0) * i / n_edge) for i in range(n_edge)]
    for k in range(32):
        pts.append((0.5 + 0.1 * math.cos(k * math.pi / 16), 0.5 + 0.1 * math.sin(k * math.pi / 16)))
    return pts


def site_card(data, t, theme):
    rng = random.Random(1405 + (0 if theme == "dark" else 7))
    W, H = 640, 300
    a = t["accent"]
    css = (".gl{animation:br 6s ease-in-out 2.6s infinite alternate;transform-origin:150px 150px}"
           "@keyframes br{to{transform:scale(1.035)}}")
    body = [f'<rect x="16" y="16" width="268" height="268" rx="16" fill="{t["glow"]}" fill-opacity="{t["glowA"]*0.5:.3f}" stroke="{t["line"]}"/>',
            f'<g class="gl">{particles(star_points(), 40, 40, 220, 220, t, rng, 1.0, 2.2, 180, 0, 1.0)}</g>']
    for (cx, cy, sx, sy) in [(26, 26, 1, 1), (274, 26, -1, 1), (26, 274, 1, -1), (274, 274, -1, -1)]:
        body.append(f'<path d="M{cx} {cy+12*sy}V{cy}H{cx+12*sx}" fill="none" stroke="{t["gold"]}" stroke-width="1.5" stroke-opacity=".8"/>')
    x = 312
    body.append('<g class="fu" style="--d:.15s">' + T("mono6", "++", 11, x, 48, t["gold"], ls=1.2) + T("mono", "/ PORTFOLIO SITE", 11, x + 22, 48, t["text3"], ls=1.2) + "</g>")
    body.append('<g class="fu" style="--d:.3s">' + T("serif", "Portfolio", 46, x - 2, 102, t["text"]) + "</g>")
    body.append('<g class="fu" style="--d:.4s">' + T("fa8", "نمونه‌کارها", 18, 612, 98, t["text3"], "end") + "</g>")
    pitch = "Projects, résumé and an interactive shell, in English and Persian. Every project has its own page with docs and releases."
    for k, line in enumerate(wrap("inter", clean(pitch), 14.5, 296)[:4]):
        body.append(f'<g class="fu" style="--d:{.45 + k*.06:.2f}s">' + T("inter", line, 14.5, x, 138 + k * 22, t["text2"]) + "</g>")
    cx = chip(body, x, 252, "mrzroot.github.io", t)
    lang = data["site"].get("language") or ""
    if lang:
        chip(body, cx, 252, lang, t, dot=LANG_COLORS.get(lang, a))
    return frame(W, H, t, "\n".join(body), css, rx=18, glow=(0.2, 0.5))


# --------------------------------------------------------------------------- mini cards (other public repos)
def mini_card(i, slug, m, t, theme):
    W, H = 640, 208
    a = t["accent"]
    body = [f'<path d="M18 30V18H30" fill="none" stroke="{t["gold"]}" stroke-width="1.5" stroke-opacity=".8"/>',
            f'<path d="M{W-18} {H-30}V{H-18}H{W-30}" fill="none" stroke="{t["gold"]}" stroke-width="1.5" stroke-opacity=".8"/>']
    x = 40
    tag = f"FORK OF {FORK_OF[slug].upper()}" if m["fork"] and slug in FORK_OF else "OPEN SOURCE"
    body.append('<g class="fu" style="--d:.1s">' + T("mono6", f"{i+1:02d}", 11, x, 44, t["gold"], ls=1.2)
                + T("mono", f"/ {len(MORE):02d} · {tag}", 11, x + 22, 44, t["text3"], ls=1.2) + "</g>")
    name = clean(slug)
    size = 30 if F["serif"].width(name, 30) <= W - 2 * x else 30 * (W - 2 * x) / F["serif"].width(name, 30)
    body.append('<g class="fu" style="--d:.2s">' + T("serif", name, size, x - 1, 84, t["text"]) + "</g>")
    desc = clean(m["desc"])
    lines = wrap("inter", desc, 14, W - 2 * x)
    if len(lines) > 3:
        lines = lines[:3]
        while F["inter"].width(lines[-1] + "…", 14) > W - 2 * x:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    for k, line in enumerate(lines):
        body.append(f'<g class="fu" style="--d:{.3 + k*.06:.2f}s">' + T("inter", line, 14, x, 112 + k * 20, t["text2"]) + "</g>")
    cx = x
    if m["lang"]:
        cx = chip(body, cx, 186, m["lang"], t, dot=LANG_COLORS.get(m["lang"], a))
    home = m["home"].replace("https://", "").rstrip("/")
    if home:
        body.append(T("mono", home, 11, W - x, 186 - 5, t["text3"], "end", .2))
    return frame(W, H, t, "\n".join(body), "", rx=18, glow=(0.15, 0.4))


# --------------------------------------------------------------------------- link badges
BADGES = [("portfolio", "mrzroot.github.io", "inter6"), ("persian", "فارسی", "fa8"), ("telegram", "Telegram", "inter6"),
          ("linkedin", "LinkedIn", "inter6")]


def badge(label, font, t):
    w = F[font].width(label, 14) + 48
    h = 36
    body = [f'<circle cx="19" cy="{h/2}" r="4" fill="{t["gold"]}"/>', T(font, label, 14, 33, h / 2 + 5, t["text"])]
    return frame(round(w), h, t, "\n".join(body), "", rx=18, glow=(0.2, 0.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = fetch()
    for theme, t in THEMES.items():
        (OUT / f"header-{theme}.svg").write_text(header(t, theme))
        for i, spec in enumerate(FLAGSHIPS):
            (OUT / f"card-{spec[0]}-{theme}.svg").write_text(card(i, spec, data["info"][spec[0]], t, theme))
        (OUT / f"stats-{theme}.svg").write_text(stats(data, t, theme))
        (OUT / f"terminal-{theme}.svg").write_text(terminal(data, t, theme))
        (OUT / f"card-site-{theme}.svg").write_text(site_card(data, t, theme))
        for i, (slug, m) in enumerate(data["more"].items()):
            (OUT / f"mini-{slug}-{theme}.svg").write_text(mini_card(i, slug, m, t, theme))
        for name, label, font in BADGES:
            (OUT / f"badge-{name}-{theme}.svg").write_text(badge(label, font, t))
        act = activity(data, t, theme)
        if act:   # if the API is unavailable keep the previous file rather than publish anything made up
            (OUT / f"activity-{theme}.svg").write_text(act)
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
