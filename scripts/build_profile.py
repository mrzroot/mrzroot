#!/usr/bin/env python3
"""Build the small, theme-aware SVGs for the github.com/mrzroot profile README:
the particle M-R-Z banner, one particle emblem per flagship, and a stats strip. Warm palette only.

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



# slug, display name, Persian name, English line, Persian line, (light colour, dark colour): warm hues only
PROJECTS = [
    ("mihanstack", "MihanStack", "میهن‌استک",
     "Local cloud for Iranian payment and SMS APIs: Zarinpal, Zibal, Kavenegar and SMS.ir with failure scenarios, chaos mode and record/replay.",
     "ابر محلی برای API های پرداخت و پیامک ایرانی: زرین‌پال، زیبال، کاوه‌نگار و SMS.ir، با سناریوی خطا، حالت آشوب و ضبط/بازپخش.",
     ("#c2540a", "#f08a3c")),
    ("dibs", "dibs", "",
     "Stops Claude Code, Codex, Cursor, Gemini CLI, Copilot and aider from reverting the edits you make by hand.",
     "جلوی ایجنت‌های کدنویسی هوش مصنوعی را می‌گیرد تا ویرایش‌های دستی شما را برنگردانند.",
     ("#cf8a0c", "#f5b942")),
    ("hamyad", "hamyad", "هم‌یاد",
     "One shared project brain for ChatGPT, Claude, Codex, Gemini, Grok, Cursor, Copilot and more: sessions, decisions and diffs, over MCP and REST.",
     "یک مغز مشترک پروژه برای همهٔ ابزارهای هوش مصنوعی: نشست‌ها، تصمیم‌ها و تغییرات، از راه MCP و REST.",
     ("#b8553a", "#e8856a")),
    ("dokhaneh", "dokhaneh", "دوخانه",
     "Publishes every release to GitHub and Iranian hosts with an Ed25519-signed manifest and a verifying fallback installer.",
     "هر نسخه را هم روی گیت‌هاب و هم روی میزبان‌های ایرانی منتشر می‌کند، با مانیفست امضاشدهٔ Ed25519 و نصب‌کنندهٔ جایگزینِ اعتبارسنج.",
     ("#a8760f", "#dba83a")),
    ("paknevis", "paknevis", "پاک‌نویس",
     "Persian text linter and auto-fixer: half-spaces, Arabic letters, punctuation, digits. CLI, pre-commit and GitHub Action.",
     "اصلاح‌گر و لینتر متن فارسی: نیم‌فاصله، حروف عربی، نقطه‌گذاری و ارقام. خط فرمان، pre-commit و GitHub Action.",
     ("#e09a12", "#ffc857")),
    ("netdoctor-ir", "netdoctor-ir", "",
     "Connectivity doctor for developers in Iran: scans dev services, ranks DNS resolvers, switches pip, npm and Docker mirrors.",
     "پزشک اتصال برای برنامه‌نویس‌های ایران: سرویس‌های توسعه را می‌سنجد، DNS ها را رتبه‌بندی می‌کند و آینه‌های pip و npm و Docker را عوض می‌کند.",
     ("#c9400f", "#f26a3a")),
    ("flowpilot", "flowpilot", "",
     "Self-hosted, code-first workflow engine: YAML in Git, cron, webhook and RSS triggers, Telegram steps, Jalali dates.",
     "موتور گردش‌کار خودمیزبان و کد-محور: YAML در Git، محرک‌های cron و webhook و RSS، گام‌های تلگرام و تاریخ جلالی.",
     ("#b0642a", "#e29a62")),
    ("sabr", "sabr", "صبر",
     "Resumable git clone, docker pull and downloads for links that keep dropping: a drop costs one step, not the whole transfer.",
     "git clone و docker pull و دانلود ازسرگرفتنی برای اتصال‌های ناپایدار: قطع شدن فقط یک گام را از بین می‌برد، نه کل انتقال را.",
     ("#c98a1b", "#efc064")),
    ("marz", "marz", "مرز",
     "Will your app work in Iran, China and Russia? Scans code for blocked and sanctioned services, with OONI data and fixes.",
     "برنامه‌ات در ایران، چین و روسیه کار می‌کند؟ کد را از نظر سرویس‌های مسدود و تحریمی می‌سنجد، با داده‌های OONI و راه‌حل.",
     ("#a8432a", "#e0735a")),
    ("whystuck", "whystuck", "",
     "Runs any command with an idle watchdog. When it hangs, says why (pager, editor, y/N prompt, password, lock) and prints the non-interactive fix.",
     "هر فرمانی را با نگهبان بی‌کاری اجرا می‌کند. وقتی گیر کند می‌گوید چرا (pager، ویرایشگر، پرسش y/N، رمز عبور، قفل) و راه‌حل غیرتعاملی را چاپ می‌کند.",
     ("#b58a10", "#f0cc5a")),
    ("shellparity", "shellparity", "",
     "Diffs your terminal shell against an AI agent's shell (PATH, versions, proxies, UTF-8, SSH, git signing) and prints the rc-file fix.",
     "شل ترمینال شما را با شل ایجنت هوش مصنوعی مقایسه می‌کند (PATH، نسخه‌ها، پروکسی، UTF-8، SSH، امضای git) و اصلاح فایل rc را چاپ می‌کند.",
     ("#d9772a", "#f5a45c")),
    ("whystale", "whystale", "",
     "Changed the code but it behaves the old way? Finds servers started before .env changed, old builds, deps and generated code.",
     "کد را عوض کردی ولی هنوز مثل قبل کار می‌کند؟ سرورهای شروع‌شده پیش از تغییر .env، بیلدها، وابستگی‌ها و کدهای تولیدشدهٔ کهنه را پیدا می‌کند.",
     ("#9c4a1a", "#d98a50")),
    ("whycached", "whycached", "",
     "Deployed but still seeing the old version? Finds which cache layer (CDN, browser, service worker, filename) serves it, with proof and the fix.",
     "دیپلوی کردی ولی هنوز نسخهٔ قدیمی را می‌بینی؟ پیدا می‌کند کدام لایهٔ کش (CDN، مرورگر، service worker، نام فایل) آن را می‌دهد، با مدرک و راه‌حل.",
     ("#dfa21c", "#ffcf5a")),
    ("persianprobe", "persianprobe", "",
     "Does your language handle Persian text the way you think? Runs the same probes through Python, Node, Perl, SQLite, Go and shows where they disagree.",
     "زبان برنامه‌نویسی‌ات متن فارسی را همان‌طور که فکر می‌کنی پردازش می‌کند؟ همین آزمون‌ها را در Python و Node و Perl و SQLite و Go اجرا می‌کند و اختلاف‌ها را نشان می‌دهد.",
     ("#96502a", "#d4895c")),
    ("whyenv", "whyenv", "",
     "Changed the env variable and nothing changed? Shows which source (shell, .env files, compose) wins in Vite, Next, dotenv and Compose, and which edit is ignored.",
     "متغیر محیطی را عوض کردی و چیزی عوض نشد؟ نشان می‌دهد کدام منبع (شل، فایل‌های .env، compose) در Vite و Next و dotenv و Compose برنده است و کدام ویرایش نادیده گرفته می‌شود.",
     ("#cf7d0e", "#f2a93b")),
]
FLAGSHIPS = [(p[0],) for p in PROJECTS]

THEMES = {
    # warm ivory paper, burnt orange / saffron dots, warm ink. No teal, no mint.
    "light": dict(bg="#faf4e6", surface="#fffaf0", line="#eadfc6", line2="#dccfae", text="#2a1d12", text2="#5a4631",
                  text3="#76614a", accent="#b8470a", gold="#8a5a08", hot="#c77a0a", glow="#f0b44a", glowA=0.22,
                  dot="#2a1d12", dotA=0.06, ink="#3a2a1e",
                  banner=[("#b84a08", .40), ("#d4860c", .30), ("#e8a91f", .14), ("#3a2a1e", .16)]),
    # deep warm black, amber / gold dots
    "dark": dict(bg="#120e0a", surface="#1a1510", line="#2a2118", line2="#3b2e20", text="#f6ecd9", text2="#c9b99f",
                 text3="#a3917a", accent="#f2b84b", gold="#e8a33a", hot="#ffd98a", glow="#e59a1f", glowA=0.14,
                 dot="#f6ecd9", dotA=0.05, ink="#ffe3a8",
                 banner=[("#f2b84b", .38), ("#e59a1f", .28), ("#ffd98a", .20), ("#d9622a", .14)]),
}
# warm language palette (no blues or cyans)
LANG_COLORS = {"Python": "#d98a0f", "TypeScript": "#b8470a", "JavaScript": "#e8a91f", "Go": "#a8760f", "Groovy": "#9c4a1a",
               "HTML": "#c9400f", "Shell": "#b58a10", "CSS": "#b8553a", "PHP": "#96502a"}

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



def fetch():
    user = gh(f"/users/{USER}") or {}
    repos = gh(f"/users/{USER}/repos?per_page=100&type=owner") or []
    info = {}
    for p in PROJECTS:
        slug = p[0]
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
    return dict(user=user, repos=repos, own=own, info=info, langs=langs)


# --------------------------------------------------------------------------- shared SVG frame
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




# --------------------------------------------------------------------------- particle helpers
def dots_paths(pts, t, rng, sizes, palette, ox, oy, sx, sy, cls_count=4):
    """Batch dots into a few <path d="M x y h0"> elements (round caps) so the file stays tiny.
    Dots are split into `cls_count` drift groups with different gentle animations."""
    buckets: dict = {}
    for i, (nx, ny) in enumerate(pts):
        x, y = ox + nx * sx, oy + ny * sy
        r = rng.choices(sizes, weights=[5, 4, 3, 1][:len(sizes)])[0]
        r2 = rng.random()
        acc = 0
        col = palette[-1][0]
        for c, w in palette:
            acc += w
            if r2 < acc:
                col = c
                break
        g = i % cls_count
        buckets.setdefault((g, col, r), []).append(f"M{x:.0f} {y:.0f}h0")
    groups = []
    for g in range(cls_count):
        inner = "".join(f'<path d="{"".join(v)}" stroke="{col}" stroke-width="{r*2:g}"/>'
                        for (gg, col, r), v in sorted(buckets.items()) if gg == g)
        groups.append(f'<g class="d{g}" stroke-linecap="round" fill="none">{inner}</g>')
    return "".join(groups)


DRIFT_CSS = (".d0{animation:a0 9s ease-in-out infinite alternate}.d1{animation:a1 11s ease-in-out infinite alternate}"
             ".d2{animation:a2 13s ease-in-out infinite alternate}.d3{animation:a3 10s ease-in-out infinite alternate}"
             "@keyframes a0{to{transform:translate(2.2px,-1.6px)}}@keyframes a1{to{transform:translate(-2px,1.8px)}}"
             "@keyframes a2{to{transform:translate(1.6px,2px)}}@keyframes a3{to{transform:translate(-1.8px,-1.4px)}}"
             "@media (prefers-reduced-motion:reduce){.d0,.d1,.d2,.d3{animation:none}}")


def banner(t, theme):
    """The particle M-R-Z, same layout as the site hero, as a static (gently drifting) dotted rendering."""
    rng = random.Random(1405)
    W, H = 1000, 350
    pts = PARTICLES["mrz"]
    # faint stray dust like the site hero
    dust_pts = [(rng.random(), rng.random()) for _ in range(60)]
    dust = "".join(f'<circle cx="{x*W:.0f}" cy="{y*H:.0f}" r="{0.7+rng.random()*1.0:.1f}" fill="{t["text3"]}" fill-opacity="{0.12+rng.random()*0.22:.2f}"/>'
                   for x, y in dust_pts)
    letters = dots_paths(pts, t, rng, [1.8, 2.3, 2.9, 3.5], t["banner"], 0, -0.12 * 480, W, 480)
    gdefs = "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLYPHS.values())
    cap = T("mono", "move along · it's particles all the way down", 11.5, W / 2, H - 14, t["text3"], "middle", 1.3)
    gdefs = "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLYPHS.values())
    GLYPHS.clear()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="M-R-Z drawn with warm particles">
<defs>
<radialGradient id="g" cx=".5" cy=".42" r=".62"><stop offset="0" stop-color="{t['glow']}" stop-opacity="{t['glowA']}"/><stop offset="1" stop-color="{t['glow']}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{t['dot']}" fill-opacity="{t['dotA']}"/></pattern>
<clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath>
{gdefs}
</defs>
<style>{DRIFT_CSS}</style>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="{t['bg']}"/>
<rect width="{W}" height="{H}" fill="url(#grid)"/>
<rect width="{W}" height="{H}" fill="url(#g)"/>
{dust}
{letters}
{cap}
</g>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{t['line2']}"/>
</svg>'''


def emblem(spec, t, theme):
    slug, name, fa, en, fap, (cl, cd) = spec
    rng = random.Random(zlib.crc32(slug.encode()))
    S = 120
    pts = PARTICLES[slug]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    w0, h0 = max(xs) - min(xs), max(ys) - min(ys)
    k = (S - 28) / max(w0, h0)
    ox = (S - w0 * k) / 2 - min(xs) * k
    oy = (S - h0 * k) / 2 - min(ys) * k
    main = cd if theme == "dark" else cl
    palette = [(main, .86), (t["ink"], .14)]
    dots = dots_paths([(x, y) for x, y in pts], t, rng, [1.0, 1.4, 1.9], palette, ox, oy, k, k, 2)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}" role="img" aria-label="{name} particle emblem">
<style>{DRIFT_CSS}</style>
<rect x=".5" y=".5" width="{S-1}" height="{S-1}" rx="20" fill="{t['surface']}" stroke="{t['line2']}"/>
<radialGradient id="g" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="{main}" stop-opacity=".12"/><stop offset="1" stop-color="{main}" stop-opacity="0"/></radialGradient>
<rect x="1" y="1" width="{S-2}" height="{S-2}" rx="19" fill="url(#g)"/>
{dots}
</svg>'''


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



# --------------------------------------------------------------------------- build
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = fetch()
    for theme, t in THEMES.items():
        (OUT / f"banner-{theme}.svg").write_text(banner(t, theme))
        for spec in PROJECTS:
            (OUT / f"emblem-{spec[0]}-{theme}.svg").write_text(emblem(spec, t, theme))
        (OUT / f"stats-{theme}.svg").write_text(stats(data, t, theme))
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
