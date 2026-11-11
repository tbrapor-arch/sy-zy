"""Open the built app in a headless browser, visit every page, report script errors; screenshots on request.

  python3 tools/smoke.py [--shots DIR]

Needs Playwright (pip install playwright) and a Chromium or Chrome (python3 -m playwright install chromium, or the
system's google-chrome).
"""
import asyncio, os, pathlib, shutil, sys
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'app/dist/index.html').as_uri()
PAGES = ['lessons', 'lesson-0', 'lesson-1', 'lesson-7', 'wave-1', 'lesson-50', 'review', 'lists', 'dict', 'drills', 'bridge', 'settings', 'books', 'read', 'video', 'vid-kaixin-1']
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None


async def main():
    errs = []
    async with async_playwright() as p:
        chrome = shutil.which('google-chrome') or shutil.which('chromium')
        b = await p.chromium.launch(**({'executable_path': chrome} if chrome else {}))
        pg = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        await pg.route('**/*', lambda r: r.abort() if not r.request.url.startswith('file:') else r.continue_())  # offline
        pg.on('pageerror', lambda e: errs.append(f'{pg.url.split("#")[-1]}: {e}'))
        for h in PAGES:
            await pg.goto(URL + '#' + h)
            await pg.wait_for_timeout(300)
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                await pg.screenshot(path=f'{SHOTS}/{h}.png')
        # a word card, add it to the lesson list, then the list and its flashcards
        await pg.goto(URL + '#lesson-1'); await pg.wait_for_timeout(300)
        await pg.click('.tok >> nth=0'); await pg.wait_for_timeout(200)
        await pg.click('#add-list'); await pg.wait_for_timeout(200)
        if SHOTS: await pg.screenshot(path=f'{SHOTS}/card.png')
        await pg.goto(URL + '#list-lessons'); await pg.wait_for_timeout(300)
        n = await pg.locator('.vtable tr').count()
        if n != 1: errs.append(f'list-lessons: {n} rows, expected 1')
        if await pg.locator('#lfc').count():   # the Flashcards button is hidden while CARDS is false
            await pg.click('#lfc'); await pg.wait_for_timeout(300)
            if SHOTS: await pg.screenshot(path=f'{SHOTS}/flashcards.png')
        # traditional characters
        await pg.evaluate("localStorage.setItem('syzy:prefs', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('syzy:prefs')||'{}'), {chars:'trad'})))")
        await pg.goto(URL + '#lesson-1'); await pg.reload(); await pg.wait_for_timeout(300)
        h1 = await pg.inner_text('h1')
        if h1 != '儂早！': errs.append(f'traditional title: {h1!r}')
        if SHOTS: await pg.screenshot(path=f'{SHOTS}/lesson-1-trad.png')
        await b.close()
    for e in errs:
        print('ERROR', e)
    print('smoke:', 'ok' if not errs else f'{len(errs)} error(s)', f'({len(PAGES)} pages)')
    sys.exit(1 if errs else 0)

asyncio.run(main())
