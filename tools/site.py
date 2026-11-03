"""Turn app/dist into the installable web app in _site/ (used by the GitHub workflow).

  python3 tools/site.py [out-dir]

Adds the home-screen icon and manifest links, copies app/pwa/ (manifest, icons, offline service worker).
The Content Security Policy of Tsheh-tû's tools/site.py comes with the app template port (sync + private module).
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_site'))
PWA = os.path.join(ROOT, 'app/pwa')
DIST = os.path.join(ROOT, 'app/dist')

html = open(os.path.join(DIST, 'index.html'), encoding='utf-8').read()
tag = '<meta name="theme-color" content="#FCFCF8">'
if tag not in html:
    sys.exit('site.py: theme-color meta not found in app/dist/index.html')
html = html.replace(tag, tag + '\n<link rel="manifest" href="manifest.webmanifest">\n<link rel="icon" href="icon-192.png">'
                    '\n<link rel="apple-touch-icon" href="icon-192.png">\n<meta name="apple-mobile-web-app-capable" content="yes">'
                    '\n<meta name="apple-mobile-web-app-title" content="书橱">', 1)
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(html)
for f in os.listdir(PWA):
    shutil.copy(os.path.join(PWA, f), OUT)
open(os.path.join(OUT, '.nojekyll'), 'w').close()
print(f'{os.path.relpath(OUT, ROOT)}: installable site')
