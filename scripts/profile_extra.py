"""Extra profile assets (tagline typer, status chips, links pills, stats dashboard, contribution heat-map,
stack chips, release/commit feed, per-project meta chips, footer wave). Called from build_profile.main().

Everything is a small self-hosted SVG: text is outlined (so Persian shapes correctly and no font is fetched),
animation is CSS inside the SVG (works through <img>, and every animation is disabled under
prefers-reduced-motion), and every number comes from the GitHub API via build_profile.fetch().
"""
from __future__ import annotations

import datetime as dt
import math

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ROLES = ["Software Engineer", "Python & TypeScript", "AI coding agents", "Persian-first tools"]
WARM = ["#d98a0f", "#b8470a", "#e8a91f", "#a8760f", "#9c4a1a", "#c9400f", "#b58a10", "#b8553a", "#96502a"]


def faNum(v):
    return str(v).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def star(cx, cy, R, r=None):
    r = r or R * 0.42
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append(f"{cx + rad * math.cos(a):.1f},{cy + rad * math.sin(a):.1f}")
    return "M" + "L".join(pts) + "Z"


def arrow(x, y, s, col):
    """small north-east arrow"""
    return (f'<path d="M{x} {y+s}L{x+s} {y}M{x+s*.2:.1f} {y}H{x+s}V{y+s*.8:.1f}" fill="none" stroke="{col}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')


def build(bp, data):
    OUT, THEMES, T, F, frame, GLYPHS = bp.OUT, bp.THEMES, bp.T, bp.F, bp.frame, bp.GLYPHS
    today = dt.date.fromisoformat(data["updated"])
    cal = data.get("cal") or {}
    days = cal.get("days", [])
    counts = {d: c for d, c in days}

    def ascii_clean(s, n):
        s = "".join(ch for ch in s if 32 <= ord(ch) < 127)
        return s if len(s) <= n else s[: n - 1].rstrip() + "..."

    def rel(date):
        try:
            n = (today - dt.date.fromisoformat(date)).days
        except Exception:
            return ""
        return "today" if n <= 0 else "yesterday" if n == 1 else f"{n} days ago" if n < 60 else f"{n // 30} months ago"

    # ---- calendar-derived numbers (all computed from the real calendar)
    ds = sorted(days)
    active = sum(1 for _, c in ds if c > 0)
    best = max([c for _, c in ds] or [0])
    longest = cur = 0
    for _, c in ds:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    cs = 0
    seq = [c for d, c in ds if d <= data["updated"]]
    i = len(seq) - 1
    if i >= 0 and seq[i] == 0:      # today may not have happened yet: streak counts back from yesterday
        i -= 1
    while i >= 0 and seq[i] > 0:
        cs += 1
        i -= 1

    def doc(name, theme, svg):
        (OUT / f"{name}-{theme}.svg").write_text(svg)

    def bare(W, H, t, body, css="", rx=18, glow=None):
        """frame() without the dotted paper if glow is None"""
        return frame(W, H, t, body, css, rx=rx, glow=glow or (0.5, 0.0))

    # =================================================================== tagline typer
    def tagline(t, theme):
        W, H = 1000, 72
        tx = 196
        rw = [F["inter6"].width(r, 30) for r in ROLES]
        maxw = max(rw) + 40
        n = len(ROLES)
        cyc = n * 3.8
        step = 100 / n
        kf, groups = [], []
        for i, (r, w) in enumerate(zip(ROLES, rw)):
            a, ty, end, fade = i * step, i * step + step * 0.28, (i + 1) * step - step * 0.1, (i + 1) * step
            ft = lambda v: f"{v:.2f}%"
            first = i == 0
            # group visibility
            kf.append(f"@keyframes v{i}{{" + (f"0%{{opacity:1}}{ft(end)}{{opacity:1}}{ft(fade)}{{opacity:0}}100%{{opacity:0}}" if first else
                      f"0%{{opacity:0}}{ft(a)}{{opacity:0}}{ft(a+.01)}{{opacity:1}}{ft(end)}{{opacity:1}}{ft(fade)}{{opacity:0}}100%{{opacity:0}}") + "}")
            # typing: curtain and caret slide right together over the text
            run = w + 6
            kf.append(f"@keyframes t{i}{{0%{{transform:translateX({0 if not first else 0}px)}}" +
                      (f"{ft(ty)}{{transform:translateX({run:.0f}px)}}100%{{transform:translateX({run:.0f}px)}}" if first else
                       f"{ft(a)}{{transform:translateX(0)}}{ft(ty)}{{transform:translateX({run:.0f}px)}}100%{{transform:translateX({run:.0f}px)}}") + "}")
            groups.append(
                f'<g class="r{i}" opacity="{1 if first else 0}">'
                + T("inter6", r, 30, tx, 46, t["text"])
                + f'<rect class="c{i}" x="{tx}" y="10" width="{maxw:.0f}" height="52" fill="{t["surface"]}" transform="translate({run:.0f} 0)"/>'
                + f'<g class="k{i}" transform="translate({run:.0f} 0)"><rect class="bl" x="{tx + 2}" y="14" width="3" height="40" rx="1.5" fill="{t["hot"]}"/></g>'
                + "</g>")
        css = "".join(f".r{i}{{animation:v{i} {cyc}s linear infinite}}.c{i},.k{i}{{animation:t{i} {cyc}s linear infinite}}" for i in range(n))
        css += "".join(kf) + ".bl{animation:bl .9s steps(1) infinite}"
        prompt = T("mono6", "mrzroot", 17, 34, 43, t["hot"]) + T("mono", "~ $", 17, 124, 43, t["text3"]) + T("mono", "whoami", 0.1, 0, 0, t["bg"])
        deco = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{t["hot"]}" fill-opacity=".5" class="fu" style="--d:{d}s"/>'
                       for x, y, r, d in [(930, 22, 2.4, .2), (952, 46, 1.6, .5), (968, 28, 2, .8), (982, 50, 1.4, 1.1), (914, 48, 1.2, 1.3)])
        body = (f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{t["surface"]}"/>' + prompt + "".join(groups) + deco)
        css += f".fu{{animation:fu 1.1s cubic-bezier(.22,1,.36,1) var(--d,0s) both}}"
        return bare(W, H, t, body, css, rx=14)

    # =================================================================== status chips (open to collaboration etc.)
    def chip_row(items, y, t, h=36, size=15, font="inter", gap=12, pulse_first=False):
        widths = [F[font].width(s, size) + (46 if pulse_first and k == 0 else 32) for k, s in enumerate(items)]
        tot = sum(widths) + gap * (len(items) - 1)
        x = (1000 - tot) / 2
        out = []
        for k, (s, w) in enumerate(zip(items, widths)):
            fill = t["hot"] if (pulse_first and k == 0) else t["text2"]
            out.append(f'<g class="fu" style="--d:{.15 + k * .1:.2f}s"><rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="{h}" rx="{h/2:.0f}" fill="{t["surface"]}" stroke="{t["hot"] if (pulse_first and k == 0) else t["line2"]}"/>')
            tx = x + 16
            if pulse_first and k == 0:
                out.append(f'<circle cx="{x+22:.0f}" cy="{y+h/2:.0f}" r="9" fill="{t["hot"]}" fill-opacity=".25" class="pulse"/><circle cx="{x+22:.0f}" cy="{y+h/2:.0f}" r="4.5" fill="{t["hot"]}"/>')
                tx = x + 36
            out.append(T(font, s, size, tx, y + h / 2 + size * 0.35, fill) + "</g>")
            x += w + gap
        return "".join(out)

    def status(t, theme):
        W, H = 1000, 108
        en = ["Open to collaboration", "Mashhad, Iran", "M.Sc. Computer Engineering", "Khorasan Razavi Chamber of Commerce"]
        fa = ["آماده‌ی همکاری", "مشهد، ایران", "کارشناسی ارشد مهندسی کامپیوتر", "اتاق بازرگانی خراسان رضوی"]
        body = chip_row(en, 8, t, pulse_first=True) + chip_row(fa, 58, t, size=15, font="fa", pulse_first=True)
        css = ".pulse{transform-box:fill-box;transform-origin:center;animation:pl 2.2s ease-out infinite}@keyframes pl{0%{transform:scale(.5);opacity:.9}100%{transform:scale(1.6);opacity:0}}"
        return bare(W, H, t, body, css, rx=0, glow=(.5, .5)).replace('<rect width="1000" height="108" fill="' + t["bg"] + '"/>', "").replace(
            f'<rect width="{W}" height="{H}" fill="url(#dots)"/>', "").replace(f'<rect width="{W}" height="{H}" fill="url(#g)"/>', "").replace(
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="0" fill="none" stroke="{t["line2"]}"/>', "")

    # =================================================================== link pills
    PILLS = [("portfolio", "Portfolio", "پورتفولیو", True), ("fa", "فارسی", "", False), ("resume", "Resume", "رزومه", False),
             ("telegram", "Telegram", "", False), ("linkedin", "LinkedIn", "", False)]

    def pill(en, fa, primary, t):
        H = 44
        wen = F["inter6" if not en.startswith("ف") else "fa8"].width(en, 16 if not en.startswith("ف") else 17)
        wfa = F["fa8"].width(fa, 16) if fa else 0
        W = int(24 + wen + (18 + wfa if fa else 0) + 14 + 16 + 20)
        fg = "#fff8ec" if primary and t["bg"] > "#888888" else (t["bg"] if primary else t["text"])
        fill = t["hot"] if primary else t["surface"]
        x = 22
        parts = [f'<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="{H/2-.75}" fill="{fill}" stroke="{t["hot"] if primary else t["line2"]}" stroke-width="1.5"/>']
        if en.startswith("ف"):
            parts.append(T("fa8", en, 17, x, 28, fg))
        else:
            parts.append(T("inter6", en, 16, x, 28, fg))
        x += wen
        if fa:
            parts.append(f'<rect x="{x+9:.0f}" y="14" width="1" height="16" fill="{fg}" fill-opacity=".35"/>')
            parts.append(T("fa8", fa, 16, x + 18, 28, fg))
            x += 18 + wfa
        parts.append(arrow(W - 30, 15, 12, fg))
        defs = "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLYPHS.values())
        GLYPHS.clear()
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
                f'<defs>{defs}</defs>' + "".join(parts) + "</svg>")

    # =================================================================== dashboard
    def dashboard(t, theme):
        W = 1000
        info, own, langs = data["info"], data["own"], data["langs"]
        stars = sum(r.get("stars", 0) for r in data["repos"])
        tiles = [
            (str(len(own)), "Public repositories", "مخزن عمومی"),
            (str(data["total_releases"]), "Releases published", "نسخه‌ی منتشرشده"),
            (str(cal.get("total", 0)), "Contributions, 12 months", "مشارکت در ۱۲ ماه"),
            (str(cal.get("prs", 0)), "Pull requests, 12 months", "درخواست ادغام"),
            (str(active), "Active days", "روز فعال"),
            (f"{cs}", "Current streak (days)", "رشته‌ی فعلی، به روز"),
            (f"{longest}", "Longest streak (days)", "بلندترین رشته، به روز"),
            (str(stars), "Stars across repos", "ستاره‌ها"),
        ]
        body = [T("mono6", "STATS", 13, 36, 44, t["gold"], ls=2),
                T("mono", f"live from the GitHub API · {data['updated']}", 13, 100, 44, t["text3"], ls=.3),
                T("fa", "آمار زنده از گیت‌هاب", 15, 964, 44, t["text3"], "end")]
        tw, th, gx, gy, x0, y0 = 218, 116, 16, 16, 36, 66
        for k, (v, en, fa) in enumerate(tiles):
            c, r = k % 4, k // 4
            x, y = x0 + c * (tw + gx), y0 + r * (th + gy)
            body.append(
                f'<g class="fu" style="--d:{.1 + k * .09:.2f}s"><rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="14" fill="{t["dot"]}" fill-opacity=".035" stroke="{t["line"]}"/>'
                f'<rect x="{x}" y="{y+22}" width="3" height="30" rx="1.5" fill="{t["hot"]}"/>'
                + T("inter6", v, 44, x + 18, y + 54, t["text"], ls=-1.2)
                + T("inter", en, 14.5, x + 18, y + 80, t["text2"])
                + T("fa", fa, 14, x + tw - 16, y + 102, t["text3"], "end") + "</g>")
        # languages by bytes
        y = y0 + 2 * (th + gy) + 18
        total = sum(langs.values()) or 1
        items = sorted(langs.items(), key=lambda kv: -kv[1])
        top = items[:6]
        rest = sum(v for _, v in items[6:])
        if rest:
            top.append(("Other", rest))
        body.append(T("mono6", "LANGUAGES", 13, 36, y + 6, t["gold"], ls=2))
        body.append(T("mono", f"by bytes · {len(own) - len(bp.GENERATED_REPOS & {r['name'] for r in own})} repos", 13, 144, y + 6, t["text3"], ls=.3))
        body.append(T("fa", "زبان‌ها بر اساس حجم کد", 15, 964, y + 6, t["text3"], "end"))
        bx, bw, by = 36, 928, y + 24
        body.append(f'<clipPath id="lb"><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6" fill="{t["line"]}"/><g clip-path="url(#lb)">')
        cx, cols = bx, []
        for k, (lang, n) in enumerate(top):
            col = bp.LANG_COLORS.get(lang) or WARM[(k + 3) % len(WARM)]
            if lang == "Other":
                col = t["text3"]
            cols.append(col)
            w = bw * n / total
            body.append(f'<rect class="lg" style="--d:{.3 + k * .12:.2f}s;transform-origin:{cx:.0f}px 0" x="{cx:.1f}" y="{by}" width="{max(w - 2, 1.5):.1f}" height="12"  fill="{col}"/>')
            cx += w
        body.append("</g>")
        lx, ly = 36, by + 40
        for (lang, n), col in zip(top, cols):
            pct = 100 * n / total
            label = f"{lang} {pct:.1f}%"
            wl = F["mono"].width(label, 13)
            if lx + wl + 30 > 964:
                lx, ly = 36, ly + 26
            body.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{col}"/>' + T("mono", label, 13, lx + 16, ly, t["text2"]))
            lx += wl + 44
        H = ly + 28
        css = ".lg{animation:gr 1.3s cubic-bezier(.22,1,.36,1) var(--d) backwards}@keyframes gr{from{transform:scaleX(0)}}"
        return bare(W, H, t, "".join(body), css)

    # =================================================================== heat map
    def heatmap(t, theme):
        W = 1000
        lv = {"light": ["#eadfc6", "#f4d9a0", "#eeb250", "#dc7d12", "#b8400a"],
              "dark": ["#2a2118", "#5c3a12", "#a9651a", "#ec962f", "#ffd05a"]}[theme]
        if not ds:
            return bare(W, 120, t, T("inter", "contribution data unavailable", 16, 36, 60, t["text2"]))
        mx = max(c for _, c in ds) or 1
        # quartiles like github: levels by fraction of the max of non-zero days
        nz = sorted(c for _, c in ds if c > 0)

        def level(c):
            if c == 0:
                return 0
            q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 1, 1]
            return 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4
        first = dt.date.fromisoformat(ds[0][0])
        cell, gap, lx, ly = 14, 3, 66, 96
        weeks = {}
        for d, c in ds:
            dd = dt.date.fromisoformat(d)
            wk = (dd - first).days // 7
            weeks.setdefault(wk, []).append((dd, c))
        body = ['<defs><rect id="c" width="14" height="14" rx="3.5"/></defs>', T("mono6", "CONTRIBUTIONS", 13, 36, 44, t["gold"], ls=2),
                T("mono", f"{cal.get('total', 0)} in the last year · best day {best} · {active} active days", 13, 190, 44, t["text3"], ls=.3),
                T("fa", "نقشه‌ی مشارکت‌های یک سال اخیر", 15, 964, 44, t["text3"], "end")]
        lastm = None
        for wk in sorted(weeks):
            x = lx + wk * (cell + gap)
            d0 = weeks[wk][0][0]
            if d0.month != lastm:
                lastm = d0.month
                if not (wk == 0 and d0.day > 14):      # a partial first month would collide with the next label
                    body.append(T("inter", MONTHS[d0.month - 1], 13, x, ly - 10, t["text3"]))
            col = []
            for dd, c in weeks[wk]:
                row = (dd.weekday() + 1) % 7      # Sunday on top like github
                y = ly + row * (cell + gap)
                is_today = dd.isoformat() == data["updated"]
                col.append(f'<use href="#c" class="l{level(c)}" x="{x}" y="{y}"/>')
                if is_today:
                    col.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3.5" fill="none" stroke="{t["hot"]}" stroke-width="1.5"/>')
            body.append(f'<g class="w" style="--i:{wk}">' + "".join(col) + "</g>")
        for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            body.append(T("inter", name, 12, 36, ly + r * (cell + gap) + 12, t["text3"]))
        gy = ly + 7 * (cell + gap) + 16
        lgx = 964 - (5 * (cell + 4)) - 80
        body.append(T("inter", "Less", 12.5, lgx, gy + 11, t["text3"], "end") if False else T("inter", "Less", 12.5, lgx, gy + 11, t["text3"]))
        for k in range(5):
            body.append(f'<use href="#c" class="l{k}" x="{lgx + 38 + k * (cell + 4)}" y="{gy}"/>')
        body.append(T("inter", "More", 12.5, lgx + 38 + 5 * (cell + 4) + 4, gy + 11, t["text3"]))
        body.append(T("mono", "private contributions are not counted · source: GitHub contribution calendar", 12, 36, gy + 11, t["text3"], ls=.2))
        H = gy + 34
        css = "".join(f".l{k}{{fill:{c}}}" for k, c in enumerate(lv))
        css += ".w{animation:wv .9s cubic-bezier(.22,1,.36,1) calc(var(--i)*22ms) backwards}@keyframes wv{from{opacity:0;transform:translateY(8px)}}"
        # gentle shimmer on the busiest cells
        css += ".l4{animation:sh 3.4s ease-in-out infinite alternate}@keyframes sh{to{opacity:.72}}"
        return bare(W, H, t, "".join(body), css)

    # =================================================================== stack chips
    STACK = [("Python", "Py"), ("TypeScript", "TS"), ("Go", "Go"), ("FastAPI", "API"), ("Node.js", "JS"), ("SQLite", "SQL"),
             ("Docker", "Dk"), ("GitHub Actions", "CI"), ("pytest", "pt"), ("WebGL", "GL"), ("MCP", "MCP"), ("Git", "Git"), ("Linux", "Lx")]

    def stack(t, theme):
        W = 1000
        x, y, rowh, h = 36, 20, 52, 42
        out = []
        for k, (name, mono) in enumerate(STACK):
            w = int(F["inter6"].width(name, 16) + 64)
            if x + w > W - 36:
                x, y = 36, y + rowh
            col = WARM[k % len(WARM)] if theme == "light" else ["#f2b84b", "#ff9a3c", "#ffd98a", "#e59a1f", "#ff7a2a", "#ffc857"][k % 6]
            fg = "#fff8ec" if theme == "light" else "#1a1008"
            out.append(f'<g class="b" style="--d:{k * .37:.2f}s"><g transform="translate({x} {y})">'
                       f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{h/2-.5}" fill="{t["surface"]}" stroke="{t["line2"]}"/>'
                       f'<rect x="8" y="8" width="{26 if len(mono) < 3 else 30}" height="26" rx="8" fill="{col}"/>'
                       + T("mono6", mono, 11 if len(mono) < 3 else 10, 8 + (26 if len(mono) < 3 else 30) / 2, 25, fg, "middle")
                       + T("inter6", name, 16, 46 + (4 if len(mono) >= 3 else 0), 27, t["text"]) + "</g></g>")
            x += w + 10
        H = y + h + 20
        css = ".b{animation:bob 4.2s ease-in-out var(--d) infinite alternate}@keyframes bob{from{transform:translateY(0)}to{transform:translateY(-3px)}}"
        css += ".fu{animation:fu 1.1s cubic-bezier(.22,1,.36,1) both}"
        return bare(W, H, t, "".join(out), css, rx=0).replace(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>', "").replace(
            f'<rect width="{W}" height="{H}" fill="url(#dots)"/>', "").replace(f'<rect width="{W}" height="{H}" fill="url(#g)"/>', "").replace(
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="0" fill="none" stroke="{t["line2"]}"/>', "")

    # =================================================================== releases + commits
    def feed(t, theme):
        W = 1000
        rels = data["releases"][:6]
        rec = data["recent"][:6]
        colw, rh, y0 = 464, 58, 76
        body = [T("mono6", "LATEST RELEASES", 13, 36, 44, t["gold"], ls=2), T("mono6", "RECENT COMMITS", 13, 520, 44, t["gold"], ls=2),
                T("fa", "آخرین نسخه‌ها", 15, 36 + colw - 12, 44, t["text3"], "end"), T("fa", "آخرین کامیت‌ها", 15, 964, 44, t["text3"], "end")]
        for k, (d, slug, tag) in enumerate(rels):
            y = y0 + k * rh
            body.append(f'<g class="fu" style="--d:{.1 + k * .08:.2f}s"><rect x="36" y="{y}" width="{colw}" height="{rh-8}" rx="12" fill="{t["dot"]}" fill-opacity=".035" stroke="{t["line"]}"/>'
                        f'<circle cx="58" cy="{y+25}" r="5" fill="{t["hot"]}"/>' + T("inter6", slug, 17, 76, y + 22, t["text"])
                        + T("inter", f"{d} · {rel(d)}", 13.5, 76, y + 41, t["text3"])
                        + f'<rect x="{36 + colw - 18 - F["mono6"].width(tag, 13.5) - 18:.0f}" y="{y+11}" width="{F["mono6"].width(tag, 13.5) + 18:.0f}" height="26" rx="13" fill="{t["hot"]}" fill-opacity=".14"/>'
                        + T("mono6", tag, 13.5, 36 + colw - 18 - F["mono6"].width(tag, 13.5) - 9, y + 29, t["hot"]) + "</g>")
        for k, c in enumerate(rec):
            y = y0 + k * rh
            msg = ascii_clean(c["msg"], 52)
            body.append(f'<g class="fu" style="--d:{.2 + k * .08:.2f}s"><rect x="520" y="{y}" width="{colw}" height="{rh-8}" rx="12" fill="{t["dot"]}" fill-opacity=".035" stroke="{t["line"]}"/>'
                        f'<circle cx="542" cy="{y+25}" r="5" fill="none" stroke="{t["hot"]}" stroke-width="2"/>'
                        + T("mono6", (c["repo"] if len(c["repo"]) <= 24 else c["repo"][:22] + ".."), 14.5, 560, y + 22, t["hot"]) + T("inter", rel(c["date"]), 12.5, 520 + colw - 16, y + 22, t["text3"], "end")
                        + T("inter", msg, 14, 560, y + 42, t["text2"]) + "</g>")
        H = y0 + max(len(rels), len(rec), 1) * rh + 14
        return bare(W, H, t, "".join(body))

    # =================================================================== per-project meta chip
    def meta(slug, i, t, theme):
        H, W = 30, 392
        main = i["lang"] or ""
        x = 2
        out = []
        out.append(f'<path d="{star(14, 15, 8.5)}" fill="{t["hot"]}"/>')
        out.append(T("inter6", str(i["stars"]), 14.5, 28, 20.5, t["text"]))
        x = 28 + F["inter6"].width(str(i["stars"]), 14.5) + 18
        if main:
            col = bp.LANG_COLORS.get(main, t["hot"])
            out.append(f'<circle cx="{x+5}" cy="15" r="5" fill="{col}"/>' + T("inter", main, 14, x + 16, 20, t["text2"]))
            x += 16 + F["inter"].width(main, 14) + 18
        if i["tag"]:
            w = F["mono6"].width(i["tag"], 13) + 16
            out.append(f'<rect x="{x:.0f}" y="3" width="{w:.0f}" height="24" rx="12" fill="{t["hot"]}" fill-opacity=".16"/>' + T("mono6", i["tag"], 13, x + 8, 20, t["hot"]))
            x += w + 10
            out.append(T("inter", i["date"], 13, x, 20, t["text3"]))
        defs = "".join(f'<path id="{g}" d="{d}"/>' for g, d in GLYPHS.values())
        GLYPHS.clear()
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"><defs>{defs}</defs>' + "".join(out) + "</svg>"

    # =================================================================== footer wave
    def footer(t, theme):
        W, H = 1000, 130
        n = 72
        cols = [t["banner"][k % 3][0] for k in range(n)]
        body = []
        for k in range(n):
            x = 20 + k * (W - 40) / (n - 1)
            amp = 16 * math.sin(k / n * math.pi * 3) + 6 * math.sin(k * .9)
            ys = [44 + amp + j * 12 for j in range(4)]
            r = 1.6 + 1.3 * ((k * 7) % 3) / 2
            path = "".join(f"M{x:.0f} {y:.0f}h0" for y in ys)
            body.append(f'<path class="wv" style="--d:{-k * .11:.2f}s" d="{path}" stroke="{cols[k]}" stroke-opacity="{.45 + .5 * ((k * 5) % 7) / 6:.2f}" stroke-width="{r*2:.1f}" stroke-linecap="round" fill="none"/>')
        body.append(T("mono", "move along · it's particles all the way down", 13, W / 2, 112, t["text3"], "middle", 1.4))
        css = ".wv{animation:fw 3.6s ease-in-out var(--d) infinite alternate}@keyframes fw{from{transform:translateY(-7px)}to{transform:translateY(7px)}}"
        return bare(W, H, t, "".join(body), css, rx=0).replace(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>', "").replace(
            f'<rect width="{W}" height="{H}" fill="url(#dots)"/>', "").replace(f'<rect width="{W}" height="{H}" fill="url(#g)"/>', "").replace(
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="0" fill="none" stroke="{t["line2"]}"/>', "")

    for theme, t in THEMES.items():
        doc("tagline", theme, tagline(t, theme))
        doc("status", theme, status(t, theme))
        for key, en, fa, primary in PILLS:
            doc("pill-" + key, theme, pill(en, fa, primary, t))
        doc("dashboard", theme, dashboard(t, theme))
        doc("heatmap", theme, heatmap(t, theme))
        doc("stack", theme, stack(t, theme))
        doc("feed", theme, feed(t, theme))
        doc("footer", theme, footer(t, theme))
        for spec in bp.PROJECTS:
            doc("meta-" + spec[0], theme, meta(spec[0], data["info"][spec[0]], t, theme))
