#!/usr/bin/env python3
"""Generate README.md from the PROJECTS table in build_profile.py (run by hand: python scripts/make_readme.py).

Project text is real markdown/HTML, never an image, so the profile stays readable even if an image is slow or blocked.
Only the banner, one small particle emblem per project and the stats strip are images (self-hosted SVG).
"""
import importlib.util
import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bp", HERE / "build_profile.py")
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)

G = "./assets/gen"
SITE = "https://mrzroot.github.io"


def pic(name, alt, extra="", mobile=False):
    ms = ""
    if mobile:      # phones get a narrow re-layout instead of a 31%-scaled desktop card
        ms = (f'<source media="(max-width: 700px) and (prefers-color-scheme: dark)" srcset="{G}/{name}-m-dark.svg">'
              f'<source media="(max-width: 700px)" srcset="{G}/{name}-m-light.svg">')
    return (f'<picture>{ms}<source media="(prefers-color-scheme: dark)" srcset="{G}/{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="{G}/{name}-light.svg">'
            f'<img alt="{html.escape(alt)}" src="{G}/{name}-light.svg"{extra}></picture>')


def row(p):
    slug, name, fa, en, fap, _ = p
    title = f"{name} · {fa}" if fa else name
    repo, page = f"https://github.com/mrzroot/{slug}", f"{SITE}/{slug}/"
    return (f'<tr>\n<td valign="top" width="88">'
            f'<a href="{repo}">{pic("emblem-" + slug, name + " particle emblem", " width=\"72\" height=\"72\"")}</a></td>\n'
            f'<td valign="top"><b><a href="{repo}">{title}</a></b> · <a href="{page}">site</a><br>\n'
            f'{pic("meta-" + slug, name + ": stars, language and latest release", " width=\"320\"")}<br>\n'
            f'{html.escape(en, quote=False)}\n'
            f'<div dir="rtl">{html.escape(fap, quote=False)}</div></td>\n</tr>')


rows = [row(p) for p in bp.PROJECTS]

MORE = [
    ("AgentForge", "agentforge", "one source of AI coding-agent rules, synced to Cursor, Claude Code, Windsurf, Copilot, Roo and Aider."),
    ("Awesome Persian Developer Resources", "awesome-persian-developer-resources", "curated hub of tools Iranian developers rely on."),
    ("Universal Video Downloader", "universal-video-downloader", "Chrome/Edge extension that saves HLS and MP4 streams, client-side."),
    ("Page Smash", "page-smash", "jetpack physics toy that smashes any webpage."),
    ("Jenkins Pipeline Examples", "jenkins", "small, readable declarative pipelines."),
]
more = "\n".join(f"- [**{n}**](https://github.com/mrzroot/{s}) · {d}" for n, s, d in MORE)
more += "\n- [**PrintBridge**](https://github.com/mrzroot/printbridge) · fork of [AnouarSbia/printbridge](https://github.com/AnouarSbia/printbridge), a local agent for silent PDF and label printing."

def link_pill(href, name, alt):
    return f'<a href="{href}">{pic("pill-" + name, alt)}</a>'


pills = "\n".join([
    link_pill(f"{SITE}/", "portfolio", "Portfolio"),
    link_pill(f"{SITE}/?lang=fa", "fa", "Persian portfolio"),
    link_pill(f"{SITE}/resume/", "resume", "Resume"),
    link_pill("https://t.me/mrzroot", "telegram", "Telegram"),
    link_pill("https://linkedin.com/in/mrzroot", "linkedin", "LinkedIn"),
])

readme = f'''<p align="center">
<a href="{SITE}/">{pic("banner", "M-R-Z drawn with warm particles: move along, it's particles all the way down", ' width="100%"')}</a>
</p>

<p align="center">
{pic("tagline", "mrzroot: Software Engineer, Python and TypeScript, AI coding agents, Persian-first tools", ' width="100%"', mobile=True)}
</p>

<h1 align="center">Mohammadreza Zare · محمدرضا زارع</h1>

<p align="center">
Software that <i>explains why</i> · نرم‌افزاری که می‌گوید <i>چرا</i>
</p>

<p align="center">
{pills}
</p>

<p align="center">
{pic("status", "Open to collaboration · Mashhad, Iran · M.Sc. Computer Engineering · Khorasan Razavi Chamber of Commerce", ' width="100%"', mobile=True)}
</p>

I'm a software engineer in Mashhad, Iran. I build **open-source developer tools** in Python and TypeScript, mostly for **AI coding agents** and for **developers in Iran**: small, well-tested tools that tell you *why* something broke. Each one has a release, docs and its own website.

<div dir="rtl">
مهندس نرم‌افزارم و در مشهد زندگی می‌کنم. ابزارهای متن‌باز توسعه می‌دهم، بیشتر با پایتون و تایپ‌اسکریپت و برای <b>ایجنت‌های کدنویسی هوش مصنوعی</b> و <b>برنامه‌نویس‌های ایرانی</b>: ابزارهای کوچک و تست‌شده که می‌گویند <b>چرا</b> چیزی خراب شده. هر کدام نسخهٔ منتشرشده، مستندات و وب‌سایت خودش را دارد.
</div>

> [!TIP]
> **Open to collaboration.** Every flagship below has issues labelled [`good first issue`](https://github.com/search?q=user%3Amrzroot+label%3A%22good+first+issue%22+state%3Aopen&type=issues), and a pull request is the fastest way to say hello.
>
> <div dir="rtl"><b>آمادهٔ همکاری‌ام.</b> هر پروژهٔ شاخص issue با برچسب <code>good first issue</code> دارد و ارسال pull request بهترین شروع آشناییست.</div>

### Now · اکنون

<table>
<tr>
<td valign="top" width="50%"><b>Building</b><br>
<a href="https://github.com/mrzroot/vazhgun">vazhgun</a>, <a href="https://github.com/mrzroot/payanlint">payanlint</a> and <a href="https://github.com/mrzroot/arjaa">arjaa</a>: offline tools for a Persian Word thesis (flipped numerals, typing and format lint, figure and citation cross-references).
<div dir="rtl"><b>در حال ساخت</b><br>
vazhgun، payanlint و arjaa: ابزارهای آفلاین برای پایان‌نامهٔ فارسی در ورد (اعداد وارونه، لینت تایپ و قالب‌بندی، ارجاع شکل و منبع).</div></td>
<td valign="top" width="50%"><b>Working at</b><br>
Programmer at the Khorasan Razavi Chamber of Commerce, Mashhad (<a href="{SITE}/resume/">resume</a>).
<div dir="rtl"><b>محل کار</b><br>
برنامه‌نویس در اتاق بازرگانی خراسان رضوی، مشهد.</div></td>
</tr>
</table>

### Flagship projects · پروژه‌های شاخص

<table>
{chr(10).join(rows)}
</table>

<sub>Stars, language and version beside each project are read from the GitHub API and refreshed daily.</sub>

### Stack · ابزارها

<p align="center">
{pic("stack", "Python, TypeScript, Go, FastAPI, Node.js, SQLite, Docker, GitHub Actions, pytest, WebGL, MCP, Git, Linux", ' width="100%"', mobile=True)}
</p>

### Live from GitHub · زنده از گیت‌هاب

<p align="center">
{pic("dashboard", "Live GitHub numbers for mrzroot: repositories, releases, contributions, pull requests, streaks, stars and language mix", ' width="100%"', mobile=True)}
</p>

<p align="center">
{pic("heatmap", "Contribution heat map for the last 52 weeks", ' width="100%"', mobile=True)}
</p>

<p align="center">
{pic("feed", "Latest releases and recent commits", ' width="100%"', mobile=True)}
</p>

### More projects · پروژه‌های بیشتر

{more}

<p align="center">
{link_pill(f"{SITE}/", "portfolio", "Portfolio")}
{link_pill("https://t.me/mrzroot", "telegram", "Telegram")}
{link_pill("https://linkedin.com/in/mrzroot", "linkedin", "LinkedIn")}
</p>

<p align="center">
{pic("footer", "move along, it's particles all the way down", ' width="100%"')}
</p>

<sub>Every picture here is a small self-hosted SVG in one warm palette, with light and dark variants; there is no external image service or counter. Text is outlined from open fonts so Persian shapes correctly everywhere, and the motion switches off when your system asks for reduced motion. The numbers are rebuilt daily by <a href="./.github/workflows/profile-cards.yml">a GitHub Action</a> running <a href="./scripts/build_profile.py">scripts/build_profile.py</a>. Language shares are by bytes across my public non-fork repositories, excluding generated site output.</sub>
'''
(HERE.parent / "README.md").write_text(readme)
print("README.md", len(readme), "bytes")
