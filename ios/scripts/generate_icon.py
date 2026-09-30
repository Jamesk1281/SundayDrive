"""Generate the Sunday Drive app icon and brand logo.

Two marks, one palette:

  * **The app icon** is a round badge — a striped low sun going down behind two
    hills, with a road winding out between them. It is the mark that survives
    the home screen: sun, hills and ring all still read at 29 px.
  * **The brand logo** is a woody wagon with a canoe on the roof, driving past
    the same sun. It is the name, literally, and the more memorable of the two
    at full size — but at 40 px it is only "a car on a sun", which is why it is
    the logo and not the icon.

Both are flat, five colours, no gradients: a patch or a sticker, not a scene.
No SF Symbols anywhere, which the Xcode licence forbids in icons and logos.

Run on macOS (no Python dependencies):
    python3 ios/scripts/generate_icon.py
writes
    docs/brand/icon.svg                  the badge, on a cream square
    docs/brand/logo.svg                  the wagon, transparent
    docs/brand/lockup-script.svg         wagon + "Sunday" script / "DRIVE" caps
    docs/brand/lockup-italic.svg         wagon + italic name + subtitle
    ios/Sources/Assets.xcassets/AppIcon.appiconset/icon-1024.png

The lockups set the name in live `<text>` with fonts that ship with macOS
(Snell Roundhand, Cochin, Futura). That is fine for choosing and for docs; a
shipped wordmark wants licensed, outlined lettering.

The PNG is rasterised with `qlmanage` (WebKit) and flattened through `sips`,
because App Store icons must be opaque and qlmanage writes RGBA.
"""

import pathlib
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
BRAND = REPO / "docs" / "brand"
PNG_OUT = REPO / "ios" / "Sources" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png"
SIZE = 1024

CREAM = "#F3E7CF"
MARIGOLD = "#F2B04A"
AMBER = "#E07B2E"   # Theme.swift's amber line, light appearance
RUST = "#B8502E"
PINE = "#2F5A47"
PINE_DARK = "#24473A"
MOSS = "#5E8763"
INK = "#2B211B"
TAN = "#C98F52"
WOOD = "#8A5A33"


def svg(body, view_box=f"0 0 {SIZE} {SIZE}"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{body}</svg>\n'


def badge(uid="badge"):
    """The app icon's mark: a ringed circle, 404 px radius about the centre."""
    return f"""<defs><clipPath id="{uid}"><circle cx="512" cy="512" r="404"/></clipPath></defs>
<circle cx="512" cy="512" r="404" fill="{CREAM}"/>
<g clip-path="url(#{uid})">
<circle cx="512" cy="520" r="230" fill="{MARIGOLD}"/>
<rect x="250" y="560" width="524" height="14" fill="{CREAM}"/>
<rect x="250" y="598" width="524" height="18" fill="{CREAM}"/>
<rect x="250" y="640" width="524" height="22" fill="{CREAM}"/>
<path d="M60 700 C 230 590, 400 600, 560 668 C 700 615, 850 600, 980 690 V 1000 H 60 Z" fill="{MOSS}"/>
<path d="M60 770 C 250 690, 400 720, 512 786 C 640 720, 800 700, 980 760 V 1000 H 60 Z" fill="{PINE}"/>
<path d="M505 786 C 610 850, 440 900, 400 1000 L 640 1000 C 610 900, 680 850, 519 786 Z" fill="{CREAM}"/>
</g>
<circle cx="512" cy="512" r="404" fill="none" stroke="{INK}" stroke-width="40"/>"""


def wagon(uid="wagon"):
    """The brand logo: a woody wagon, canoe on the roof, before a low sun."""
    body = ("M196 668 L196 526 Q196 488 232 486 L566 486 C604 487 622 504 640 540 "
            "L658 574 C742 576 802 586 828 606 C846 620 848 650 842 668 "
            "Q838 690 814 690 L220 690 Q196 690 196 668 Z")
    fenders = "M244 690 A84 84 0 0 1 412 690 M630 690 A84 84 0 0 1 798 690"
    return f"""<defs><clipPath id="{uid}"><circle cx="512" cy="540" r="340"/></clipPath></defs>
<circle cx="512" cy="540" r="340" fill="{MARIGOLD}"/>
<g clip-path="url(#{uid})"><rect x="150" y="690" width="724" height="220" fill="{AMBER}"/></g>
<path d="M232 468 Q520 404 812 468 Q520 494 232 468 Z" fill="{RUST}"/>
<path d="M300 486 v-14 M720 486 v-14" stroke="{INK}" stroke-width="10"/>
<path d="{body}" fill="{PINE}"/>
<rect x="196" y="592" width="400" height="68" fill="{TAN}"/>
<path d="M196 592 H596 V660 H196 M330 592 V660 M462 592 V660" fill="none" stroke="{WOOD}" stroke-width="10"/>
<rect x="228" y="512" width="100" height="58" rx="10" fill="{CREAM}"/>
<rect x="344" y="512" width="104" height="58" rx="10" fill="{CREAM}"/>
<rect x="464" y="512" width="100" height="58" rx="10" fill="{CREAM}"/>
<path d="M580 512 L598 512 C612 514 624 536 636 570 L580 570 Z" fill="{CREAM}"/>
<circle cx="826" cy="628" r="12" fill="{CREAM}"/>
<rect x="180" y="664" width="30" height="14" rx="6" fill="{INK}"/>
<rect x="826" y="664" width="32" height="14" rx="6" fill="{INK}"/>
<path d="{fenders} Z" fill="{PINE}"/>
<path d="{fenders}" fill="none" stroke="{PINE_DARK}" stroke-width="8"/>
<circle cx="328" cy="690" r="60" fill="{INK}"/><circle cx="714" cy="690" r="60" fill="{INK}"/>
<circle cx="328" cy="690" r="24" fill="{CREAM}"/><circle cx="714" cy="690" r="24" fill="{CREAM}"/>
<rect x="110" y="746" width="804" height="16" rx="8" fill="{INK}"/>"""


def icon():
    # Scaled up so the ring sits close to the squircle mask's edge.
    return svg(f'<rect width="{SIZE}" height="{SIZE}" fill="{CREAM}"/>'
               f'<g transform="translate(512 512) scale(1.12) translate(-512 -512)">{badge()}</g>')


def lockup(style):
    if style == "script":
        # Compact: the mark matches the height of the two lines, and DRIVE
        # tucks under "Sund", clear of the y's descender.
        mark = f'<g transform="translate(10,20) scale(0.27)">{wagon()}</g>'
        text = (f'<text x="290" y="170" font-family="Snell Roundhand" font-weight="bold" '
                f'font-size="150" fill="{INK}">Sunday</text>'
                f'<text x="306" y="252" font-family="Futura" font-weight="bold" '
                f'font-size="58" letter-spacing="17" fill="{RUST}">DRIVE</text>')
        return svg(mark + text, "0 0 800 300")
    mark = f'<g transform="translate(40,40) scale(0.31)">{wagon()}</g>'
    text = (f'<text x="390" y="215" font-family="Cochin" font-style="italic" '
            f'font-size="120" fill="{INK}">Sunday Drive</text>'
            f'<text x="396" y="275" font-family="Futura" font-weight="500" '
            f'font-size="30" letter-spacing="10" fill="{RUST}">THE SCENIC ROUTE, ON PURPOSE</text>')
    return svg(mark + text, "0 0 1200 380")


def rasterise(svg_path, png_path):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["qlmanage", "-t", "-s", str(SIZE), "-o", tmp, str(svg_path)],
                       check=True, capture_output=True)
        thumb = pathlib.Path(tmp) / (svg_path.name + ".png")
        flat = pathlib.Path(tmp) / "flat.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "100",
                        str(thumb), "--out", str(flat)], check=True, capture_output=True)
        subprocess.run(["sips", "-s", "format", "png", str(flat), "--out", str(png_path)],
                       check=True, capture_output=True)


if __name__ == "__main__":
    BRAND.mkdir(parents=True, exist_ok=True)
    outputs = {
        "icon.svg": icon(),
        "logo.svg": svg(wagon()),
        "lockup-script.svg": lockup("script"),
        "lockup-italic.svg": lockup("italic"),
    }
    for name, text in outputs.items():
        (BRAND / name).write_text(text)
        print((BRAND / name).relative_to(REPO))
    rasterise(BRAND / "icon.svg", PNG_OUT)
    print(PNG_OUT.relative_to(REPO))
