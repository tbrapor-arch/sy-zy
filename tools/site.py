"""Turn app/dist into the installable web app in _site/ (used by the GitHub workflow).

  python3 tools/site.py [out-dir]

Adds the home-screen icon and manifest links, copies app/pwa/ (manifest, icons, offline service worker).
Puts a Content Security Policy in the page, as in Tsheh-tû: only the page's own inline script (by hash, recomputed at
each build), blob: scripts (the private module), run; the page talks only to GitHub's API (gist sync,
private module). A new outside source has to be added below, or the browser refuses it.
"""
import base64, hashlib, os, re, shutil, sys

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
hashes = ' '.join("'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode('utf-8')).digest()).decode() + "'"
                  for m in re.finditer(r'<script>(.*?)</script>', html, re.S))
if not hashes:
    sys.exit('site.py: no inline script found, the CSP would block the app')
rules = {
    'default-src': "'self'",
    'script-src': f"{hashes} blob:",
    'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
    'font-src': "'self' data: https://fonts.gstatic.com",
    'img-src': "'self' data: blob: https:",
    'media-src': "'self' blob: https:",
    'connect-src': "'self' https://api.github.com https://gist.githubusercontent.com https://fonts.googleapis.com https://fonts.gstatic.com",
    'worker-src': "'self'",
    'manifest-src': "'self'",
    'object-src': "'none'",
    'base-uri': "'none'",
}
meta = '<meta http-equiv="Content-Security-Policy" content="' + '; '.join(f'{k} {v}' for k, v in rules.items()) + '">'
html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + meta, 1)
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(html)
for f in os.listdir(PWA):
    shutil.copy(os.path.join(PWA, f), OUT)
open(os.path.join(OUT, '.nojekyll'), 'w').close()
print(f'{os.path.relpath(OUT, ROOT)}: installable site')
