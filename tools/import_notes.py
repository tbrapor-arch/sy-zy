"""Bring the app's "book notes" back into the database.

    python3 build/import_notes.py syzy-book-notes-2026-10-20.json

For every word you checked in the app:
  - "Matches my book"  -> course/verified.tsv   (word, IPA, book): the reading is confirmed by a book
  - "My book says …"   -> course/book_notes.tsv (word, current IPA, the book's spelling, a proposed IPA, book, note)

The proposed IPA is found by reading the book's spelling back through the Wugniu and Qian tables
(syllable by syllable, the tone kept from the current reading). Spellings from other systems get no
proposal. Nothing changes in the app until a line is copied into data/overrides.tsv:
    word <tab> IPA <tab> book <tab> note
then rebuild:  python3 build/build_db.py && python3 build/build_app.py
"""
import json, sys, re, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import romanize as R

ROOT = pathlib.Path(__file__).resolve().parent.parent

# every syllable the lexicon uses, spelled both ways -> its IPA without tone
rev = {'wugniu': collections.defaultdict(set), 'qian': collections.defaultdict(set)}
for line in open(ROOT / 'data/raw/zaonhe.txt', encoding='utf8'):
    for syl in line.rstrip('\n').split('\t')[1].split(' '):
        s = R.from_bars(syl)
        try:
            body = re.sub(r'\d+$', '', s)
            rev['wugniu'][R.wugniu_syl(s)].add(body)
            rev['qian'][R.qian_syl(s)].add(body)
        except ValueError:
            pass


def segment(text, table):
    """Split a spelling into known syllables (longest match, any split that works)."""
    text = re.sub(r'[^a-z]', '', text.lower())
    best = {0: []}
    for i in range(len(text)):
        if i not in best:
            continue
        for j in range(len(text), i, -1):
            if text[i:j] in table and j not in best:
                best[j] = best[i] + [text[i:j]]
    return best.get(len(text))


def propose(says, ipa):
    tones = [re.search(r'\d+$', s).group() if re.search(r'\d+$', s) else '' for s in ipa.split()]
    for system in ('wugniu', 'qian'):
        parts = [p for p in re.split(r'[\s\-]+', says.lower()) if p] if system == 'wugniu' else None
        if not parts or not all(p in rev[system] for p in parts):
            parts = segment(says, rev[system])
        if parts and len(parts) == len(tones):
            bodies = [sorted(rev[system][p])[0] for p in parts]
            return ' '.join(b + t for b, t in zip(bodies, tones)), system
    return '', ''


def main(path):
    d = json.load(open(path, encoding='utf8'))
    if d.get('app') != 'syzy-book-notes':
        raise SystemExit('not a 书橱 book notes file')
    ver, diff = [], []
    for n in d['notes']:
        if n.get('ok'):
            ver.append([n['word'], n['ipa'], n.get('book', ''), n.get('at', '')])
        else:
            p, system = propose(n['says'], n['ipa'])
            diff.append([n['word'], n['ipa'], n['says'], p, system, n.get('book', ''), n.get('note', ''), n.get('at', '')])
    for name, rows, head in [('verified.tsv', ver, 'word\tipa\tbook\tdate'),
                             ('book_notes.tsv', diff, 'word\tcurrent_ipa\tbook_says\tproposed_ipa\tread_as\tbook\tnote\tdate')]:
        f = ROOT / 'course' / name
        new = not f.exists()
        with open(f, 'a', encoding='utf8') as out:
            if new:
                out.write(head + '\n')
            for r in rows:
                out.write('\t'.join(r) + '\n')
        print(f'{len(rows)} lines added to data/{name}')


if __name__ == '__main__':
    main(sys.argv[1])
