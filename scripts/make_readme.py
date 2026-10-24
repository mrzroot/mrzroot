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


def pic(name, alt, extra=""):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{G}/{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="{G}/{name}-light.svg">'
            f'<img alt="{html.escape(alt)}" src="{G}/{name}-light.svg"{extra}></picture>')


def row(p):
    slug, name, fa, en, fap, _ = p
    title = f"{name} · {fa}" if fa else name
    repo, page = f"https://github.com/mrzroot/{slug}", f"{SITE}/{slug}/"
    return (f'<tr>\n<td valign="top" width="88">'
            f'<a href="{repo}">{pic("emblem-" + slug, name + " particle emblem", " width=\"72\" height=\"72\"")}</a></td>\n'
            f'<td valign="top"><b><a href="{repo}">{title}</a></b> · <a href="{page}">site</a><br>\n'
            f'{html.escape(en, quote=False)}\n'
            f'<div dir="rtl"><sub>{html.escape(fap, quote=False)}</sub></div></td>\n</tr>')


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

readme = f'''<p align="center">
<a href="{SITE}/">{pic("banner", "M-R-Z drawn with warm particles: move along, it's particles all the way down", ' width="100%"')}</a>
</p>

<p align="center">
<b>Mohammadreza Zare</b> · <b>محمدرضا زارع</b><br>
Software that <i>explains why</i> · نرم‌افزاری که می‌گوید <i>چرا</i>
</p>

<p align="center">
<a href="{SITE}/"><b>Portfolio</b></a> ·
<a href="{SITE}/?lang=fa"><b>فارسی</b></a> ·
<a href="{SITE}/resume/"><b>Resume</b></a> ·
<a href="https://t.me/mrzroot"><b>Telegram</b></a> ·
<a href="https://linkedin.com/in/mrzroot"><b>LinkedIn</b></a>
</p>

I'm a software engineer in Mashhad, Iran (M.Sc. Computer Engineering). I build **open-source developer tools** in Python and TypeScript, mostly for **AI coding agents** and for **developers in Iran**: small, well-tested tools that tell you *why* something broke. Each has a release, docs and its own website.

<div dir="rtl">ابزارهای متن‌باز توسعه می‌دهم، بیشتر برای <b>ایجنت‌های کدنویسی هوش مصنوعی</b> و <b>برنامه‌نویس‌های ایرانی</b>؛ ابزارهای کوچک و تست‌شده که می‌گویند <b>چرا</b> چیزی خراب شده. هر کدام نسخهٔ منتشرشده، مستندات و وب‌سایت خودش را دارد.</div>

### Flagship projects · پروژه‌های شاخص

<table>
{chr(10).join(rows)}
</table>

<sub>Want to contribute? Every flagship has issues labelled <a href="https://github.com/search?q=user%3Amrzroot+label%3A%22good+first+issue%22+state%3Aopen&type=issues"><b>good first issue</b></a>.</sub>

<div dir="rtl"><sub>می‌خواهید مشارکت کنید؟ هر پروژهٔ شاخص issue با برچسب <b>good first issue</b> دارد.</sub></div>

### More projects · پروژه‌های بیشتر

{more}

### Live from GitHub

{pic("stats", "Live GitHub stats for mrzroot: flagship stars, repositories, releases and languages", ' width="100%"')}

<sub>The banner, emblems and stats are small self-hosted SVGs in a warm palette, rebuilt daily by <a href="./.github/workflows/profile-cards.yml">a GitHub Action</a> from <a href="./scripts/build_profile.py">scripts/build_profile.py</a>; no external image service. Project text above is plain markdown.</sub>
'''
(HERE.parent / "README.md").write_text(readme)
print("README.md", len(readme), "bytes")
