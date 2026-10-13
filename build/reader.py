"""Reading packs for 《弄堂》 (胡宝谈, 2011), the novel written in Shanghainese.

The novel's text is NOT put in the app. The reader opens the reader's own copy of the book (the .epub)
on their device; the app ships only a "pack" per chapter: where the words start and end, which
database entry each word is, the author's inline readings, and an English translation.
Paragraphs are matched by a fingerprint of their text, so a different edition simply shows as "not matched".

Private inputs (kept out of git, see .gitignore):
  reader/longtang/book.epub       your copy of the book
Inputs in git:
  reader/longtang/glossary.tsv    hand glosses for the book's words
  reader/longtang/chNN.txt        English translation of chapter NN, one line per paragraph
"""
import re, zipfile, html, pathlib

HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')


def fnv(s):
    """32-bit FNV-1a over UTF-16 code units: the app computes the same in JavaScript."""
    h = 0x811c9dc5
    for ch in s:
        for cu in (ch.encode('utf-16-le')[i:i + 2] for i in range(0, len(ch.encode('utf-16-le')), 2)):
            h ^= int.from_bytes(cu, 'little')
            h = (h * 0x01000193) & 0xffffffff
    return h


def norm(s):
    return re.sub(r'\s+', '', s)


def chapters_from_epub(path):
    """[(headword line, [paragraph texts])] in reading order, the way the app extracts them."""
    z = zipfile.ZipFile(path)
    opf_name = next(n for n in z.namelist() if n.endswith('.opf'))
    opf = z.read(opf_name).decode('utf8')
    base = opf_name.rsplit('/', 1)[0] + '/' if '/' in opf_name else ''
    items = dict(re.findall(r'<item[^>]*?id="([^"]+)"[^>]*?href="([^"]+)"', opf))
    items.update({i: h for h, i in re.findall(r'<item[^>]*?href="([^"]+)"[^>]*?id="([^"]+)"', opf)})
    spine = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)
    out = []
    for idref in spine:
        name = base + items[idref]
        doc = z.read(name).decode('utf8', 'ignore')
        for m in re.finditer(r'<(h2|p)\b[^>]*>(.*?)</\1>', doc, re.S):
            text = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
            if m.group(1) == 'h2':
                out.append([text, []])
            elif out and text:
                out[-1][1].append(text)
    return out


def clean(text):
    """Remove the author's [readings]; return (clean text, {index of the character they follow: reading})."""
    ann, outs, i = {}, [], 0
    for m in re.finditer(r'\[([^\]]+)\]', text):
        outs.append(text[i:m.start()])
        pos = len(''.join(outs)) - 1
        ann[pos] = (ann[pos] + '/' if pos in ann else '') + m.group(1)
        i = m.end()
    outs.append(text[i:])
    return ''.join(outs), ann


def segment(text, cost):
    """Cheapest split of a paragraph into words. cost(word) -> number or None if not a word."""
    n = len(text)
    best = [(0.0, None)] + [(float('inf'), None)] * n
    for i in range(n):
        if best[i][0] == float('inf'):
            continue
        if not HAN.match(text[i]):
            j = i + 1
            while j < n and not HAN.match(text[j]) and text[j].isalnum() and text[i].isalnum():
                j += 1
            c = best[i][0] + 0.1
            if c < best[j][0]:
                best[j] = (c, i)
            continue
        for L in range(1, 7):
            w = text[i:i + L]
            if len(w) < L or not all(HAN.match(x) for x in w):
                break
            k = cost(w)
            if k is None:
                continue
            if best[i][0] + k < best[i + L][0]:
                best[i + L] = (best[i][0] + k, i)
    toks, j = [], n
    while j > 0:
        i = best[j][1]
        toks.append(text[i:j]); j = i
    return toks[::-1]
