"""Assemble the app into one self-contained page: app/dist/index.html (style + data + script inline).

The style is 冊櫥 Tsheh-tû's, copied verbatim (app/style/base.css): same colours, same layout, same fonts. Only the
Chinese fallbacks change: Iansui (Tsheh-tû's Hàn-jī font) has no simplified characters, so the glyphs it lacks come
from LXGW WenKai, the same Klee One design, subset to what the app uses and embedded (font 'SyzyExt', like
Tsheh-tû's 'TaigiExt'). Pieces only this app has are in app/style/extra.css.
Fonts: `sh data/fetch_fonts.sh` (pinned, not committed); without them the build warns and falls back to Noto Sans SC.
"""
import base64, io, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
css = (ROOT / 'app/style/base.css').read_text(encoding='utf8')
SWAP = [   # order matters: the second string is also inside the first
    ('"Iansui", "Noto Sans TC", "TaigiExt", "PingFang TC", sans-serif',
     '"Iansui", "SyzyExt", "Noto Sans SC", "PingFang SC", sans-serif'),
    ('"TailoSans", "Noto Sans", "Iansui", "Noto Sans TC", "TaigiExt", system-ui, sans-serif',
     '"TailoSans", "Noto Sans", "Iansui", "SyzyExt", "Noto Sans SC", system-ui, sans-serif'),
    ('"Noto Sans TC", "TaigiExt", "PingFang TC", sans-serif', '"Noto Sans SC", "PingFang SC", sans-serif'),   # Rose
    ('"Nunito", "Noto Sans", "Noto Sans TC", "TaigiExt", sans-serif', '"Nunito", "Noto Sans", "Noto Sans SC", sans-serif'),
]
for a, b in SWAP:
    if a not in css:
        raise SystemExit(f'style swap not found: {a}')
    css = css.replace(a, b, 1)

css += (ROOT / 'app/style/extra.css').read_text(encoding='utf8')

data = (ROOT / 'app/build/data.js').read_text(encoding='utf8')
js = (ROOT / 'app/src/app.js').read_text(encoding='utf8') + (ROOT / 'app/src/sync.js').read_text(encoding='utf8') + (ROOT / 'app/src/module.js').read_text(encoding='utf8')
def tailo_font_css():
    """Tsheh-tû's embedded Noto Sans (app/fonts/tailo-noto-sans.woff2), same name, same use."""
    b64 = base64.b64encode((ROOT / 'app/fonts/tailo-noto-sans.woff2').read_bytes()).decode()
    return (f"@font-face{{font-family:'TailoSans';font-weight:400 800;font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def ext_font_css(text):
    """'SyzyExt': the LXGW WenKai glyphs of every Chinese character in the app that Iansui does not have."""
    fdir = ROOT / 'data/raw/fonts'
    ian, wk = fdir / 'Iansui-Regular.ttf', fdir / 'LXGWWenKai-Regular.ttf'
    if not (ian.exists() and wk.exists()):
        print('WARNING: fonts missing (sh data/fetch_fonts.sh): simplified characters fall back to Noto Sans SC')
        return ''
    from fontTools import subset
    from fontTools.ttLib import TTFont
    have = set(TTFont(ian).getBestCmap())
    need = sorted({ord(c) for c in text if (0x3400 <= ord(c) <= 0x9fff or 0xf900 <= ord(c) <= 0xfaff or ord(c) >= 0x20000)
                   and ord(c) not in have and unicodedata.category(c) != 'Cn'})
    font = TTFont(wk)
    cmap = font.getBestCmap()
    got = [c for c in need if c in cmap]
    if len(got) < len(need):
        print('not in LXGW WenKai either:', ''.join(chr(c) for c in need if c not in cmap))
    sub = subset.Subsetter(subset.Options(flavor='woff2', layout_features=[], name_IDs=['*']))
    sub.populate(unicodes=got)
    sub.subset(font)
    font.flavor = 'woff2'
    buf = io.BytesIO()
    font.save(buf)
    print(f'embedded {len(got)} characters Iansui lacks ({len(buf.getvalue()) // 1024} KB)')
    rng = ','.join(f'U+{c:X}' for c in got)
    return (f"@font-face{{font-family:'SyzyExt';font-display:swap;src:url(data:font/woff2;base64,"
            f"{base64.b64encode(buf.getvalue()).decode()}) format('woff2');unicode-range:{rng};}}")


css = css.replace('/*__FONTS__*/', tailo_font_css() + '\n' + ext_font_css(data + js), 1)

html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>书橱 Sy-zy</title>
<meta name="theme-color" content="#FCFCF8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Iansui&family=Atkinson+Hyperlegible:wght@400;700&family=Noto+Sans:wght@400;600;700&family=Noto+Sans+SC:wght@400;700;900&family=Nunito:wght@600;800;900&display=swap">
<style>
{css}
</style></head><body>
<div class="shell">
  <nav class="rail" aria-label="Sections">
    <div class="logo"><div class="mark">书</div><div><b>书橱</b><small>Sy-zy · 上海闲话</small></div></div>
    <div class="tabs" id="tabs"></div>
  </nav>
  <main id="main"></main>
</div>
<aside class="sheet" id="sheet" aria-label="Word" aria-hidden="true"></aside>
<div class="toast" id="toast" hidden></div>
<script>
{data}
{js}
</script>
</body></html>
'''
(ROOT / 'app/dist').mkdir(parents=True, exist_ok=True)
(ROOT / 'app/dist/index.html').write_text(html, encoding='utf8')
print('app/dist/index.html', len(html) // 1024, 'KB · publish with tools/site.py')
