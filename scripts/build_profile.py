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
import re
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
     "ابرِ محلی برای API‌های پرداخت و پیامک ایران: زرین‌پال، زیبال، کاوه‌نگار و SMS.ir، همراه با سناریوهای خطا، حالت آشوب و ضبط و بازپخش.",
     ("#c2540a", "#f08a3c")),
    ("dibs", "dibs", "",
     "Stops Claude Code, Codex, Cursor, Gemini CLI, Copilot and aider from reverting the edits you make by hand.",
     "نمی‌گذارد ایجنت‌های کدنویسی هوش مصنوعی (Claude Code، Codex، Cursor، Gemini CLI، Copilot و aider) ویرایش‌های دستی شما را برگردانند.",
     ("#cf8a0c", "#f5b942")),
    ("hamyad", "hamyad", "هم‌یاد",
     "One shared project brain for ChatGPT, Claude, Codex, Gemini, Grok, Cursor, Copilot and more: sessions, decisions and diffs, over MCP and REST.",
     "یک حافظهٔ مشترک پروژه برای ChatGPT، Claude، Codex، Gemini، Grok، Cursor، Copilot و بقیه: نشست‌ها، تصمیم‌ها و تغییرات، از طریق MCP و REST.",
     ("#b8553a", "#e8856a")),
    ("dokhaneh", "dokhaneh", "دوخانه",
     "Publishes every release to GitHub and Iranian hosts with an Ed25519-signed manifest and a verifying fallback installer.",
     "هر نسخه را هم روی گیت‌هاب و هم روی میزبان‌های ایرانی منتشر می‌کند، با مانیفست امضاشده با Ed25519 و نصب‌کنندهٔ جایگزینی که صحت فایل را بررسی می‌کند.",
     ("#a8760f", "#dba83a")),
    ("paknevis", "paknevis", "پاک‌نویس",
     "Persian text linter and auto-fixer: half-spaces, Arabic letters, punctuation, digits. CLI, pre-commit and GitHub Action.",
     "اصلاح‌گر و لینتر متن فارسی: نیم‌فاصله، حروف عربی، نقطه‌گذاری و ارقام. خط فرمان، pre-commit و GitHub Action.",
     ("#e09a12", "#ffc857")),
    ("netdoctor-ir", "netdoctor-ir", "",
     "Connectivity doctor for developers in Iran: scans dev services, ranks DNS resolvers, switches pip, npm and Docker mirrors.",
     "پزشکِ اتصال برای برنامه‌نویس‌های ایران: سرویس‌های توسعه را می‌سنجد، DNSها را رتبه‌بندی می‌کند و آینه‌های pip و npm و Docker را عوض می‌کند.",
     ("#c9400f", "#f26a3a")),
    ("flowpilot", "flowpilot", "",
     "Self-hosted, code-first workflow engine: YAML in Git, cron, webhook and RSS triggers, Telegram steps, Jalali dates.",
     "موتور گردش‌کار خودمیزبان و کدمحور: YAML در Git، محرک‌های cron و webhook و RSS، گام‌های تلگرام و تقویم جلالی.",
     ("#b0642a", "#e29a62")),
    ("sabr", "sabr", "صبر",
     "Resumable git clone, docker pull and downloads for links that keep dropping: a drop costs one step, not the whole transfer.",
     "git clone، docker pull و دانلودِ ازسرگرفتنی برای اتصال‌های ناپایدار: قطع شدن فقط یک گام را از بین می‌برد، نه کل انتقال را.",
     ("#c98a1b", "#efc064")),
    ("marz", "marz", "مرز",
     "Will your app work in Iran, China and Russia? Scans code for blocked and sanctioned services, with OONI data and fixes.",
     "برنامه‌ات در ایران، چین و روسیه کار می‌کند؟ کد را از نظر سرویس‌های مسدود و تحریمی بررسی می‌کند، با داده‌های OONI و پیشنهاد راه‌حل.",
     ("#a8432a", "#e0735a")),
    ("whystuck", "whystuck", "",
     "Runs any command with an idle watchdog. When it hangs, says why (pager, editor, y/N prompt, password, lock) and prints the non-interactive fix.",
     "هر فرمانی را با یک نگهبانِ بی‌حرکتی اجرا می‌کند. وقتی گیر کند می‌گوید چرا (pager، ویرایشگر، پرسش y/N، رمز عبور، قفل) و راه‌حل غیرتعاملی را چاپ می‌کند.",
     ("#b58a10", "#f0cc5a")),
    ("shellparity", "shellparity", "",
     "Diffs your terminal shell against an AI agent's shell (PATH, versions, proxies, UTF-8, SSH, git signing) and prints the rc-file fix.",
     "شل ترمینال شما را با شل ایجنت هوش مصنوعی مقایسه می‌کند (PATH، نسخه‌ها، پروکسی، UTF-8، SSH، امضای git) و اصلاح لازم برای فایل rc را چاپ می‌کند.",
     ("#d9772a", "#f5a45c")),
    ("whystale", "whystale", "",
     "Changed the code but it behaves the old way? Finds servers started before .env changed, old builds, deps and generated code.",
     "کد را عوض کردی ولی هنوز مثل قبل کار می‌کند؟ سرورهایی را که پیش از تغییر .env راه افتاده‌اند، و بیلدها، وابستگی‌ها و کدهای تولیدشدهٔ کهنه را پیدا می‌کند.",
     ("#9c4a1a", "#d98a50")),
    ("whycached", "whycached", "",
     "Deployed but still seeing the old version? Finds which cache layer (CDN, browser, service worker, filename) serves it, with proof and the fix.",
     "دیپلوی کردی ولی هنوز نسخهٔ قدیمی را می‌بینی؟ پیدا می‌کند کدام لایهٔ کش (CDN، مرورگر، service worker، نام فایل) آن را می‌دهد، با مدرک و راه‌حل.",
     ("#dfa21c", "#ffcf5a")),
    ("persianprobe", "persianprobe", "",
     "Does your language handle Persian text the way you think? Runs the same probes through Python, Node, Perl, SQLite, Go and shows where they disagree.",
     "زبان برنامه‌نویسی‌ات متن فارسی را همان‌طور که فکر می‌کنی پردازش می‌کند؟ همین آزمون‌ها را در Python، Node، Perl، SQLite و Go اجرا می‌کند و اختلاف‌ها را نشان می‌دهد.",
     ("#96502a", "#d4895c")),
    ("whyenv", "whyenv", "",
     "Changed the env variable and nothing changed? Shows which source (shell, .env files, compose) wins in Vite, Next, dotenv and Compose, and which edit is ignored.",
     "متغیر محیطی را عوض کردی و چیزی عوض نشد؟ نشان می‌دهد کدام منبع (شل، فایل‌های .env، compose) در Vite و Next و dotenv و Compose برنده است و کدام ویرایش نادیده گرفته می‌شود.",
     ("#cf7d0e", "#f2a93b")),
    ("vazhgun", "vazhgun", "واژگون",
     "Persian thesis in Word: finds paragraphs where typed order and drawn order differ (۲-۳ shown as ۳-۲, left-to-right tables) and writes an explicit fixed copy.",
     "پایان‌نامهٔ فارسی در ورد: پاراگراف‌هایی را پیدا می‌کند که ترتیب تایپ‌شده و نمایش‌داده‌شده‌شان فرق دارد (۲-۳ که ۳-۲ دیده می‌شود، جدول چپ‌به‌راست) و نسخهٔ اصلاح‌شدهٔ صریح می‌نویسد.",
     ("#b4432f", "#ea7d5e")),
    ("payanlint", "payanlint", "پایان‌لینت",
     "Lints a Persian Word thesis: half-spaces, Arabic ي/ك, digit sets, complex-script font and size, margins, captions, page numbers; safe --fix on a copy.",
     "پایان‌نامهٔ فارسی در ورد را لینت می‌کند: نیم‌فاصله، «ي» و «ك» عربی، دستهٔ رقم، قلم و اندازهٔ complex-script، حاشیه، شرح شکل، شمارهٔ صفحه؛ --fix امن روی نسخه.",
     ("#8f7712", "#dcc24c")),
    ("arjaa", "arjaa", "ارجاع",
     "Checks figure and table numbers and mentions, and in-text citations against the reference list, in a Persian .docx, with Jalali and Gregorian years.",
     "شمارهٔ شکل و جدول و ارجاع به آن‌ها، و ارجاع‌های متنی را در برابر فهرست منابع در یک .docx فارسی بررسی می‌کند، با سال شمسی و میلادی.",
     ("#a85a1a", "#ee9f55")),
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


def compact(d: str) -> str:
    """Rewrite an absolute integer SVG path (M L H V Q C Z) as relative commands with minimal separators."""
    toks = re.findall(r"[MLHVQCZ]|-?\d+", d)
    out, i, x, y, sx, sy, prev, cmd = [], 0, 0, 0, 0, 0, "", ""
    nargs = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}

    def fmt(nums):
        r = ""
        for n in nums:
            t = str(n)
            r += t if (not r or t[0] == "-") else " " + t
        return r
    while i < len(toks):
        if toks[i] in nargs:
            c = toks[i]
            i += 1
        else:                        # implicit repeat of the previous command (after M it means L)
            c = "L" if cmd == "M" else cmd
        cmd = c
        n = nargs[c]
        a = [int(v) for v in toks[i:i + n]]
        i += n
        if c == "Z":
            out.append("z")
            x, y, prev = sx, sy, "z"
            continue
        if c == "H":
            rel = [a[0] - x]; x = a[0]
        elif c == "V":
            rel = [a[0] - y]; y = a[0]
        else:
            rel = [v - (x if k % 2 == 0 else y) for k, v in enumerate(a)]
            x, y = a[-2], a[-1]
        if c == "M":
            sx, sy = x, y
        lc = c.lower()
        out.append(lc + fmt(rel))
        prev = lc
    return "".join(out)
class Font:
    def __init__(self, file: str):
        data = (HERE / "fonts" / file).read_bytes()
        self.tt = TTFont(HERE / "fonts" / file)
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self.q = 360 / self.upem          # outlines are stored on a 360-unit em: plenty for text <= 40px, far smaller files
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
            pen = SVGPathPen(self.gs, ntos=lambda v, q=self.q: str(round(v * q)))
            self.gs[name].draw(pen)
            GLYPHS[key] = (f"{self.id}{len(GLYPHS)}", compact(pen.getCommands()))
        return GLYPHS[key][0]

    def use(self, s: str, size: float, x: float, y: float, anchor: str = "start", ls: float = 0) -> str:
        infos, pos = self.shape(s)
        k = size / 360
        w = self.width(s, size, ls)
        x0 = x - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
        parts, cx = [], 0.0
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            if self.gs[name].width and name not in ("space", "uni200C", "uni00A0"):
                gid = self.glyph(name)
                oy = f' y="{round(-p.y_offset * self.q)}"' if p.y_offset else ""
                parts.append(f'<use href="#{gid}" x="{round((cx + p.x_offset) * self.q)}"{oy}/>')
            elif name not in ("space", "uni200C", "uni00A0"):
                gid = self.glyph(name)
                parts.append(f'<use href="#{gid}" x="{round((cx + p.x_offset) * self.q)}"/>')
            cx += p.x_advance + ls / (k * self.q)
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



def gql(query: str):
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        return None
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "User-Agent": USER, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("data")
    except Exception:
        return None


CACHE = OUT / "data.json"
GENERATED_REPOS = {"mrzroot.github.io", "mrzroot"}   # build output / the profile repo itself: not "my work" for language stats


def calendar():
    """Last-12-months contribution calendar (GraphQL; needs a token, the Action's GITHUB_TOKEN is enough)."""
    q = ('query{user(login:"%s"){contributionsCollection{totalCommitContributions totalIssueContributions '
         'totalPullRequestContributions totalPullRequestReviewContributions contributionCalendar{totalContributions '
         'weeks{contributionDays{date contributionCount}}}}}}' % USER)
    d = gql(q)
    try:
        c = d["user"]["contributionsCollection"]
        cal = c["contributionCalendar"]
        days = [(x["date"], x["contributionCount"]) for w in cal["weeks"] for x in w["contributionDays"]]
        return dict(total=cal["totalContributions"], commits=c["totalCommitContributions"], prs=c["totalPullRequestContributions"],
                    issues=c["totalIssueContributions"], reviews=c["totalPullRequestReviewContributions"], days=days)
    except Exception:
        return None


def fetch():
    """Everything the cards show comes from the GitHub API; if a call fails the last good value from
    assets/gen/data.json is kept, so a flaky run never replaces real numbers with zeros."""
    old = {}
    if CACHE.exists():
        try:
            old = json.loads(CACHE.read_text())
        except Exception:
            old = {}
    user = gh(f"/users/{USER}") or old.get("user") or {}
    repos = gh(f"/users/{USER}/repos?per_page=100&type=owner") or old.get("repos") or []
    repos = [dict(name=r["name"], fork=r.get("fork", False), language=r.get("language"), stars=r.get("stargazers_count", 0),
                  forks=r.get("forks_count", 0), pushed=(r.get("pushed_at") or "")[:10]) if "stargazers_count" in r else r for r in repos]
    info, releases = {}, []
    for p in PROJECTS:
        slug = p[0]
        r = next((x for x in repos if x["name"] == slug), None) or {}
        rels = gh(f"/repos/{USER}/{slug}/releases?per_page=30")
        prev = old.get("info", {}).get(slug, {})
        if rels is None:
            tag, date, n = prev.get("tag", ""), prev.get("date", ""), prev.get("releases", 0)
            rl = prev.get("rel_list", [])
        else:
            rl = [(x["tag_name"], (x.get("published_at") or "")[:10]) for x in rels if not x.get("draft")]
            tag, date, n = (rl[0] if rl else ("", "")) + (len(rl),)
        info[slug] = dict(stars=r.get("stars", prev.get("stars", 0)), forks=r.get("forks", 0), lang=r.get("language") or prev.get("lang", ""),
                          tag=tag, date=date, releases=n, rel_list=rl, pushed=r.get("pushed", ""))
        releases += [(d, slug, t) for t, d in rl]
    releases.sort(reverse=True)
    own = [r for r in repos if not r.get("fork")]
    # languages by bytes across own public repos (excluding generated site output)
    langs = {}
    got = False
    for r in own:
        if r["name"] in GENERATED_REPOS:
            continue
        l = gh(f"/repos/{USER}/{r['name']}/languages")
        if l is not None:
            got = True
            for k, v in l.items():
                langs[k] = langs.get(k, 0) + v
    if not got:
        langs = old.get("langs", {})
    # latest commit message of the most recently pushed repos
    recent, seen, failed = [], set(), 0
    cand = sorted([r for r in own if r["name"] not in GENERATED_REPOS and r.get("pushed")], key=lambda r: r["pushed"], reverse=True)[:10]
    for r in cand:
        c = gh(f"/repos/{USER}/{r['name']}/commits?per_page=5")
        if c is None:
            failed += 1
            continue
        for item in c:
            cm = item["commit"]
            msg = cm["message"].splitlines()[0].strip()
            if not msg or msg.lower().startswith(("chore: update", "merge ")) or msg in seen:
                continue                     # skip bot noise and the same sweep commit repeated across repos
            seen.add(msg)
            recent.append(dict(repo=r["name"], msg=msg, date=cm["committer"]["date"][:10], ts=cm["committer"]["date"]))
    recent = sorted(recent, key=lambda x: x["ts"], reverse=True)[:6]
    if failed or not recent:
        recent = old.get("recent", recent)
    cal = calendar() or old.get("cal")
    data = dict(user=user, repos=repos, own=own, info=info, langs=langs, releases=releases, recent=recent, cal=cal,
                total_releases=sum(v["releases"] for v in info.values()), updated=dt.date.today().isoformat())
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({k: v for k, v in data.items()}, ensure_ascii=False, separators=(",", ":")))
    return data


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
def dots_paths(pts, t, rng, sizes, palette, ox, oy, sx, sy, cls_count=4, wrap=False):
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
        grp = f'<g class="d{g}" stroke-linecap="round" fill="none">{inner}</g>'
        groups.append(f'<g class="i{g}">{grp}</g>' if wrap else grp)
    return "".join(groups)


DRIFT_CSS = (".d0{animation:a0 9s ease-in-out infinite alternate}.d1{animation:a1 11s ease-in-out infinite alternate}"
             ".d2{animation:a2 13s ease-in-out infinite alternate}.d3{animation:a3 10s ease-in-out infinite alternate}"
             "@keyframes a0{to{transform:translate(2.2px,-1.6px)}}@keyframes a1{to{transform:translate(-2px,1.8px)}}"
             "@keyframes a2{to{transform:translate(1.6px,2px)}}@keyframes a3{to{transform:translate(-1.8px,-1.4px)}}"
             "@media (prefers-reduced-motion:reduce){.d0,.d1,.d2,.d3{animation:none}}")


BANNER_CSS = (
    # four interleaved dot groups settle in from different directions (so the letters "condense"), then drift and twinkle
    ".i0{animation:in0 2.8s cubic-bezier(.22,1,.36,1) backwards}.i1{animation:in1 3s cubic-bezier(.22,1,.36,1) .12s backwards}"
    ".i2{animation:in2 3.2s cubic-bezier(.22,1,.36,1) .24s backwards}.i3{animation:in3 2.9s cubic-bezier(.22,1,.36,1) .36s backwards}"
    "@keyframes in0{from{transform:translate(-30px,-16px);opacity:0}}@keyframes in1{from{transform:translate(26px,-20px);opacity:0}}"
    "@keyframes in2{from{transform:translate(-20px,24px);opacity:0}}@keyframes in3{from{transform:translate(28px,18px);opacity:0}}"
    ".d0{animation:a0 9s ease-in-out infinite alternate,k0 4.1s ease-in-out infinite alternate}"
    ".d1{animation:a1 11s ease-in-out infinite alternate,k1 5.3s ease-in-out infinite alternate}"
    ".d2{animation:a2 13s ease-in-out infinite alternate,k0 6.7s ease-in-out infinite alternate}"
    ".d3{animation:a3 10s ease-in-out infinite alternate,k1 4.7s ease-in-out infinite alternate}"
    "@keyframes a0{to{transform:translate(2.6px,-1.8px)}}@keyframes a1{to{transform:translate(-2.4px,2px)}}"
    "@keyframes a2{to{transform:translate(1.8px,2.4px)}}@keyframes a3{to{transform:translate(-2px,-1.6px)}}"
    "@keyframes k0{to{opacity:.72}}@keyframes k1{from{opacity:.78}}"
    # embers rising behind the letters
    ".e0{animation:rise 15s linear infinite}.e1{animation:rise 19s linear -7s infinite}.e2{animation:rise 23s linear -13s infinite}"
    "@keyframes rise{0%{transform:translateY(24px);opacity:0}15%{opacity:1}80%{opacity:1}100%{transform:translateY(-150px);opacity:0}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")


def banner(t, theme):
    """The particle M-R-Z, same layout as the site hero: dots condense on load, drift/twinkle, embers rise."""
    rng = random.Random(1405)
    W, H = 1000, 350
    pts = PARTICLES["mrz"]
    embers = []
    for g in range(3):
        c = "".join(f'<circle cx="{rng.random()*W:.0f}" cy="{H*0.35 + rng.random()*H*0.7:.0f}" r="{0.8+rng.random()*1.3:.1f}"/>' for _ in range(16))
        embers.append(f'<g class="e{g}" fill="{t["banner"][g % len(t["banner"])][0]}" fill-opacity="{0.35 + 0.1 * g:.2f}">{c}</g>')
    letters = dots_paths(pts, t, rng, [1.8, 2.3, 2.9, 3.5], t["banner"], 0, -0.12 * 480, W, 480, wrap=True)
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
<style>{BANNER_CSS}</style>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="{t['bg']}"/>
<rect width="{W}" height="{H}" fill="url(#grid)"/>
<rect width="{W}" height="{H}" fill="url(#g)"/>
{"".join(embers)}
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


# --------------------------------------------------------------------------- build
def main():
    import sys
    sys.path.insert(0, str(HERE))
    import profile_extra
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("stats-*.svg"):          # replaced by dashboard-*.svg
        old.unlink()
    data = fetch()
    for theme, t in THEMES.items():
        (OUT / f"banner-{theme}.svg").write_text(banner(t, theme))
        for spec in PROJECTS:
            (OUT / f"emblem-{spec[0]}-{theme}.svg").write_text(emblem(spec, t, theme))
    profile_extra.build(sys.modules[__name__], data)
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
