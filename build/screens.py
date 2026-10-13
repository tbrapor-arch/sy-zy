import asyncio, sys
from playwright.async_api import async_playwright
URL = 'file:///home/claude/shanghainese/app/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        for h in ['lessons', 'lesson-0', 'lesson-1', 'dict', 'bridge', 'settings', 'review']:
            await pg.goto(URL + '#' + h); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f'/home/claude/shots/{h}.png')
        await pg.goto(URL + '#lesson-1'); await pg.wait_for_timeout(400)
        await pg.click('.tok >> nth=6'); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/home/claude/shots/card.png')
        await pg.goto(URL + '#dict'); await pg.fill('#q', 'bhakxiang'); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/home/claude/shots/search.png')
        print('\n'.join(errs) or 'no errors')
        await b.close()
asyncio.run(main())
