"""Build the App Store screenshots with a headline header, and a search-result preview.

Reads the four raw 6.9" captures beside this file (1320 x 2868) and writes

    captioned/<n>-<name>.jpg     the upload set: cream header, headline, and the
                                 whole capture in a phone outline below it
    header-banner.jpg            2400 x 1200: icon, name and subtitle beside
                                 three phones, for the landing page and posts
    search-preview-light.png     the first three as an App Store search result
    search-preview-dark.png      would show them, at iPhone 16 Pro size (@3x)

Run on macOS with Google Chrome installed (no Python dependencies):
    python3 app-store-screenshots/build.py

Pages are laid out in HTML and rasterised by headless Chrome at exactly the
output size, then flattened to JPEG through `sips`, because App Store Connect
refuses screenshots with an alpha channel.

The search preview is a mock-up for judging the first three at the size people
see them (each about 115 pt wide). It is not a real App Store page and is not
for upload or publication.
"""

import html
import pathlib
import subprocess
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
ICON = REPO / "ios" / "Sources" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png"
OUT = HERE / "captioned"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

W, H = 1320, 2868

# generate_icon.py's palette
CREAM = "#F3E7CF"
RUST = "#B8502E"
INK = "#2B211B"
PINE = "#2F5A47"

NAME = "Sunday Drive"
SUBTITLE = "The scenic route, on purpose"

# (raw capture, headline with the accent in *stars*, the line under it).
# Claims follow docs/app-store-listing.md: the trade is against the app's own
# fastest route, "best-scoring" not "most beautiful", and New England is said
# in the first frame because only the first three show in search. The accent
# always takes the second line, so the three headers line up side by side.
SHOTS = [
    ("1-route-comparison.jpg",
     "Trade minutes for *the view*",
     "Every road in New England is scored for scenery. One slider sets what the view is worth to you."),
    ("2-loop.jpg",
     "Nowhere to be? *Take a loop.*",
     "Pick how long you have. It plans a round trip over the best-scoring roads nearby, and brings you home."),
    ("3-driving.jpg",
     "Every turn, *out loud*",
     "Spoken directions, the next turn always on screen, and a new route if you miss one."),
    ("4-home.jpg",
     "Somewhere, or *nowhere at all*",
     "Search for a destination, or loop from where you are. Free, with no account and no ads."),
]


def headline_html(text):
    plain, accent, rest = (text.split("*") + ["", ""])[:3]
    return f'{html.escape(plain)}<em>{html.escape(accent)}</em>{html.escape(rest)}'


def phone_css():
    return f""".phone{{position:absolute;background:{INK};box-shadow:0 40px 90px rgba(43,33,27,.28)}}
.phone img{{display:block;width:100%}}
.phone i{{position:absolute;background:{INK};border-radius:4px}}"""


def phone_html(src, screen_w, left, top, style=""):
    """The whole phone: the capture inside an ink bezel, with side buttons.

    Proportions are the 6.9" screen's: corners 1/8 of the width, the bezel
    1/50, the buttons placed as on the hardware.
    """
    screen_h = round(screen_w * H / W)
    bezel = round(screen_w / 50)
    radius = round(screen_w / 8)
    b = max(4, round(screen_w / 160))  # button depth
    def btn(side, y, h):
        x = f"left:-{b}px" if side == "l" else f"right:-{b}px"
        return f'<i style="{x};top:{round(screen_h * y)}px;width:{b + 2}px;height:{round(screen_h * h)}px"></i>'
    buttons = btn("l", .16, .035) + btn("l", .23, .065) + btn("l", .315, .065) + btn("r", .25, .1)
    return (f'<div class="phone" style="left:{left}px;top:{top}px;width:{screen_w}px;padding:{bezel}px;'
            f'border-radius:{radius + bezel}px;{style}">{buttons}'
            f'<img src="{src.as_uri()}" style="height:{screen_h}px;border-radius:{radius}px"></div>')


def screenshot_page(raw, headline, sub):
    # The whole phone fits under the header, 110 px clear of the foot.
    top, foot = 660, 110
    screen_w = round((H - top - foot) / (H / W + 2 / 50))
    left = (W - screen_w - 2 * round(screen_w / 50)) // 2
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:{CREAM}}}
body{{font-family:-apple-system,"SF Pro Display",system-ui,sans-serif;color:{INK};position:relative}}
.head{{position:absolute;left:96px;right:96px;top:150px}}
h1{{margin:0;font-size:128px;line-height:1.02;font-weight:800;letter-spacing:-0.025em}}
h1 em{{font-style:normal;color:{RUST};display:block}}
p{{margin:34px 0 0;font-size:50px;line-height:1.3;font-weight:500;color:rgba(43,33,27,.72);letter-spacing:-0.005em}}
{phone_css()}
</style></head><body>
<div class="head"><h1>{headline_html(headline)}</h1><p>{html.escape(sub)}</p></div>
{phone_html(HERE / raw, screen_w, left, top)}
</body></html>"""


BANNER_W, BANNER_H = 2400, 1200


def banner_page():
    """The header banner: icon, name and subtitle left, three phones right."""
    small, big = 430, 500
    def h(w):
        return round(w * H / W) + 2 * round(w / 50)
    mid_top = (BANNER_H - h(big)) // 2
    side_top = (BANNER_H - h(small)) // 2 + 40
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{BANNER_W}px;height:{BANNER_H}px;overflow:hidden;background:{CREAM}}}
body{{font-family:-apple-system,"SF Pro Display",system-ui,sans-serif;color:{INK};position:relative}}
.copy{{position:absolute;left:150px;top:0;bottom:0;width:900px;display:flex;flex-direction:column;justify-content:center}}
.copy img{{width:220px;height:220px;border-radius:50px;box-shadow:0 18px 40px rgba(43,33,27,.18)}}
h1{{margin:56px 0 0;font-size:150px;line-height:1;font-weight:800;letter-spacing:-0.03em}}
h2{{margin:22px 0 0;font-size:66px;line-height:1.1;font-weight:700;color:{RUST};letter-spacing:-0.015em}}
p{{margin:44px 0 0;font-size:40px;line-height:1.35;font-weight:500;color:rgba(43,33,27,.72)}}
p b{{color:{INK};font-weight:700}}
{phone_css()}
</style></head><body>
<div class="copy"><img src="{ICON.as_uri()}">
<h1>{NAME}</h1><h2>{SUBTITLE}</h2>
<p>Every road in New England, scored for scenery.<br><b>Free on iPhone.</b> No account, no ads.</p></div>
{phone_html(HERE / SHOTS[1][0], small, 1210, side_top, "transform:rotate(-6deg)")}
{phone_html(HERE / SHOTS[2][0], small, 1890, side_top, "transform:rotate(6deg)")}
{phone_html(HERE / SHOTS[0][0], big, 1525, mid_top, "z-index:2;box-shadow:0 50px 110px rgba(43,33,27,.35)")}
</body></html>"""


def search_page(shots, dark):
    bg, fg, dim, line, field, btn, btn_fg = (
        ("#000000", "#FFFFFF", "rgba(235,235,245,.6)", "rgba(84,84,88,.6)", "#1C1C1E", "#2C2C2E", "#0A84FF")
        if dark else
        ("#FFFFFF", "#000000", "rgba(60,60,67,.6)", "rgba(60,60,67,.29)", "#EEEEF0", "#EEEEF0", "#007AFF"))
    thumbs = "".join(f'<img src="{s.as_uri()}">' for s in shots)
    ghost = "rgba(127,127,127,.18)"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:390px;height:844px;overflow:hidden;background:{bg}}}
body{{font-family:-apple-system,system-ui,sans-serif;color:{fg};-webkit-font-smoothing:antialiased;position:relative}}
.status{{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 34px 0 44px;font-weight:600;font-size:17px}}
.status .di{{width:124px;height:36px;border-radius:20px;background:#000;position:absolute;left:133px;top:11px}}
.bar{{display:flex;align-items:center;gap:10px;padding:6px 16px 10px}}
.field{{flex:1;height:36px;border-radius:10px;background:{field};display:flex;align-items:center;padding:0 8px;gap:6px;font-size:17px}}
.field svg{{flex:none}}
.cancel{{color:{btn_fg};font-size:17px}}
.row{{display:flex;align-items:center;gap:12px;padding:10px 20px 0}}
.row img.icon{{width:62px;height:62px;border-radius:14px;border:.5px solid {line}}}
.meta{{flex:1;min-width:0}}
.name{{font-size:16px;font-weight:600;letter-spacing:-.01em}}
.sub{{font-size:13px;color:{dim};margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cat{{font-size:12px;color:{dim};margin-top:4px}}
.get{{background:{btn};color:{btn_fg};font-weight:700;font-size:15px;border-radius:16px;padding:6px 20px}}
.shots{{display:flex;gap:8px;padding:14px 20px 0}}
.shots img{{flex:1;width:0;aspect-ratio:1320/2868;border-radius:12px;border:.5px solid {line};object-fit:cover}}
.next{{padding:22px 20px 0;display:flex;gap:12px;align-items:center;border-top:.5px solid {line};margin:22px 0 0 20px;padding-left:0}}
.g{{background:{ghost};border-radius:6px}}
.tabs{{position:absolute;bottom:0;left:0;right:0;height:83px;border-top:.5px solid {line};background:{bg};display:flex;padding-top:8px;font-size:10px;color:{dim}}}
.tabs>div{{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px}}
.tabs i{{width:26px;height:24px;border-radius:6px;background:{ghost};display:block}}
.tabs .on{{color:{btn_fg}}} .tabs .on i{{background:{btn_fg}}}
</style></head><body>
<div class="status"><span>9:41</span><span class="di"></span><svg width="70" height="13" viewBox="0 0 70 13" fill="{fg}"><rect x="0" y="8" width="3" height="5" rx="1"/><rect x="5" y="6" width="3" height="7" rx="1"/><rect x="10" y="3" width="3" height="10" rx="1"/><rect x="15" y="0" width="3" height="13" rx="1"/><path d="M32 12.5 28 8.4a5.8 5.8 0 0 1 8 0zM24.6 5a10.6 10.6 0 0 1 14.8 0l-1.7 1.7a8.2 8.2 0 0 0-11.4 0z"/><rect x="44" y="1" width="22" height="11" rx="3.5" fill="none" stroke="{fg}" stroke-opacity=".4"/><rect x="46" y="3" width="18" height="7" rx="2"/><rect x="67" y="4.5" width="1.6" height="4" rx=".8" fill-opacity=".4"/></svg></div>
<div class="bar"><div class="field">
<svg width="16" height="16" viewBox="0 0 16 16"><circle cx="6.5" cy="6.5" r="5" fill="none" stroke="{dim}" stroke-width="2"/><path d="M10.3 10.3 15 15" stroke="{dim}" stroke-width="2" stroke-linecap="round"/></svg>
<span>scenic drive</span></div><span class="cancel">Cancel</span></div>
<div class="row"><img class="icon" src="{ICON.as_uri()}"><div class="meta">
<div class="name">{NAME}</div><div class="sub">{SUBTITLE}</div><div class="cat">Navigation</div></div>
<span class="get">Get</span></div>
<div class="shots">{thumbs}</div>
<div class="next"><div class="g" style="width:62px;height:62px;border-radius:14px"></div>
<div style="flex:1"><div class="g" style="width:60%;height:14px"></div><div class="g" style="width:80%;height:11px;margin-top:8px"></div></div>
<div class="g" style="width:72px;height:30px;border-radius:16px"></div></div>
<div class="shots"><div class="g" style="flex:1;height:180px"></div><div class="g" style="flex:1;height:180px"></div><div class="g" style="flex:1;height:180px"></div></div>
<div class="tabs"><div><i></i>Today</div><div><i></i>Games</div><div><i></i>Apps</div><div><i></i>Arcade</div><div class="on"><i></i>Search</div></div>
</body></html>"""


def render(page_html, out_png, width, height, scale=1):
    # A throwaway profile, so a Chrome the user has open can't collide with it.
    with tempfile.TemporaryDirectory() as profile, \
            tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page_html)
        f.close()
        src = pathlib.Path(f.name)
        try:
            _chrome(profile, src, out_png, width, height, scale)
        finally:
            src.unlink()


def _chrome(profile, src, out_png, width, height, scale):
    # Chrome 154 writes the screenshot and then often never exits, so wait for
    # its "written to file" line and close it ourselves.
    log = pathlib.Path(profile) / "stderr.log"
    with open(log, "w") as err:
        proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--user-data-dir={profile}", "--no-first-run", "--use-mock-keychain",
             "--no-default-browser-check", "--disable-extensions",
             "--allow-file-access-from-files", f"--force-device-scale-factor={scale}",
             f"--window-size={width},{height}", f"--screenshot={out_png}",
             "--default-background-color=00000000", src.as_uri()],
            stdout=subprocess.DEVNULL, stderr=err)
        try:
            for _ in range(240):
                if "written to file" in log.read_text() or proc.poll() is not None:
                    break
                time.sleep(0.25)
        finally:
            proc.terminate()
            proc.wait()
    if "written to file" not in log.read_text():
        raise SystemExit(f"Chrome failed rendering {out_png}:\n{log.read_text()[-2000:]}")


def main():
    OUT.mkdir(exist_ok=True)
    finished = []
    for raw, headline, sub in SHOTS:
        png = OUT / (pathlib.Path(raw).stem + ".png")
        render(screenshot_page(raw, headline, sub), png, W, H)
        jpg = png.with_suffix(".jpg")
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                        str(png), "--out", str(jpg)], check=True, capture_output=True)
        png.unlink()
        finished.append(jpg)
        print(jpg.relative_to(REPO))
    banner = HERE / "header-banner.png"
    render(banner_page(), banner, BANNER_W, BANNER_H)
    jpg = banner.with_suffix(".jpg")
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                    str(banner), "--out", str(jpg)], check=True, capture_output=True)
    banner.unlink()
    print(jpg.relative_to(REPO))
    for dark in (False, True):
        out = HERE / f"search-preview-{'dark' if dark else 'light'}.png"
        render(search_page(finished[:3], dark), out, 390, 844, scale=3)
        print(out.relative_to(REPO))


if __name__ == "__main__":
    main()
