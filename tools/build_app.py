"""Assemble the app into one self-contained page: app/dist/index.html (style + data + script inline).

The style starts from 冊櫥 Tsheh-tû's (app/style/base.css), recoloured: Huangpu-river teal ink instead of blue,
simplified-character fonts instead of the Taiwanese ones, plus the pieces only this app has (app/style/extra.css).
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
css = (ROOT / 'app/style/base.css').read_text(encoding='utf8')
SWAP = [
    ('--grid: #E3E9F6;', '--grid: #E1EBE8;'),
    ('--brand: #2347B5; --brand-ink: #FFFFFF; --brand-soft: #E5EBFA;', '--brand: #12655F; --brand-ink: #FFFFFF; --brand-soft: #DCEEEA;'),
    ('--line: #1A2233;', '--line: #16302D;'), ('--text: #1A2233;', '--text: #16302D;'), ('--sub: #586276;', '--sub: #536663;'),
    ('--soft-line: #CBD3E4;', '--soft-line: #C6D6D2;'),
    ('--bg: #15171D; --grid: #1F2330;', '--bg: #121918; --grid: #1B2523;'),
    ('--surface: #1C1F27; --line: #C9D1E6; --soft-line: #343A4C;', '--surface: #19221F; --line: #C3D9D4; --soft-line: #2F3F3B;'),
    ('--text: #E7EAF2; --sub: #9AA3B8; --brand: #8FA8FF; --brand-ink: #10152A; --brand-soft: #232B47;',
     '--text: #E5EFEC; --sub: #97ABA6; --brand: #6CCFC1; --brand-ink: #0B1F1D; --brand-soft: #18332F;'),
    ('"Iansui", "Noto Sans TC", "TaigiExt", "PingFang TC", sans-serif', '"Noto Serif SC", "Songti SC", "STSong", serif'),
    ('"Noto Sans", "Iansui", "Noto Sans TC", "TaigiExt", system-ui, sans-serif', '"Noto Sans", "Noto Sans SC", "PingFang SC", system-ui, sans-serif'),
    ('"Noto Sans TC", "TaigiExt", "PingFang TC", sans-serif', '"Noto Sans SC", "PingFang SC", sans-serif'),
    ('"Nunito", "Noto Sans", "Noto Sans TC", "TaigiExt", sans-serif', '"Nunito", "Noto Sans", "Noto Sans SC", sans-serif'),
    ('/* full Latin Extended + combining marks for Tâi-lô */', '/* Latin + IPA */'),
]
for a, b in SWAP:
    if a not in css:
        raise SystemExit(f'style swap not found: {a}')
    css = css.replace(a, b)
css += (ROOT / 'app/style/extra.css').read_text(encoding='utf8')

data = (ROOT / 'app/build/data.js').read_text(encoding='utf8')
js = (ROOT / 'app/src/app.js').read_text(encoding='utf8') + (ROOT / 'app/src/sync.js').read_text(encoding='utf8') + (ROOT / 'app/src/module.js').read_text(encoding='utf8')
html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>书橱 Sy-zy</title>
<meta name="theme-color" content="#FCFCF8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Noto+Sans:wght@400;600;700&family=Noto+Sans+SC:wght@400;700;900&family=Noto+Serif+SC:wght@500;700;900&family=Nunito:wght@600;800;900&display=swap">
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
