"""How much of the common vocabulary the lessons already teach, and what to teach next (as in Tsheh-tû).

  python3 tools/coverage.py [TOP]                      # step A: data/build/core_vocab.tsv (make vocab)
  python3 tools/coverage.py [TOP] --private ../syzy-private
                                                       # + step B: real Shanghainese frequencies from the owner's
                                                       #   books, read locally and printed here only, never written

A word counts as taught once it is declared in a lesson's new_words or used in a dialogue. Mandarin words (md) count
through their Shanghainese equivalent and written Mandarin (lit) is left out. The list of words to teach next shows
Shanghainese words and false friends first, then the rest by rank.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')


def taught_words():
    seen = set()
    for p in sorted(glob.glob(os.path.join(ROOT, 'course/lessons/[0-9][0-9][0-9].yaml'))):
        y = yaml.safe_load(open(p, encoding='utf8'))
        texts = [y['title']['hanzi']] + [d['hanzi'] for d in y['dialogue']] + [w['hanzi'] for w in y.get('new_words') or []]
        for t in texts:
            for tok in t.split():
                if HAN.search(tok):
                    seen.add(re.sub(r'\[[^\]]*\]$', '', tok))
    return seen


def main():
    argv = sys.argv[1:]
    if '--private' in argv:
        i = argv.index('--private'); argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    top = int(args[0]) if args else 500
    seen = taught_words()
    path = os.path.join(ROOT, 'data/build/core_vocab.tsv')
    if not os.path.exists(path):
        sys.exit('data/build/core_vocab.tsv is missing: run make vocab')
    rows = []
    for line in open(path, encoding='utf8'):
        if line.startswith('#'):
            continue
        r, w, typ, say, en = (line.rstrip('\n').split('\t') + [''] * 5)[:5]
        rows.append((int(r), w, typ, say, en))
    def covered(w, typ, say):
        return w in seen or (typ == 'md' and any(s in seen for s in say.split('、')))
    real = [x for x in rows if x[2] not in ('md', 'lit')]
    print(f'Taught so far: {len(seen)} words.  Common vocabulary (step A, jieba ranks carried to Shanghainese):')
    for n in (100, 300, 1000, 2000):
        part = [x for x in real if x[0] <= n]
        got = sum(1 for x in part if covered(x[1], x[2], x[3]))
        print(f'  top {n:>4}: {got}/{len(part)} ({100 * got // max(1, len(part))}%)')
    missing = [x for x in real if x[0] <= top and not covered(x[1], x[2], x[3])]
    missing.sort(key=lambda x: (x[2] not in ('sh', 'ff'), x[0]))
    print(f'\nNot taught yet, top {top} (Shanghainese words and false friends first):')
    for r, w, typ, say, en in missing[:40]:
        print(f'  #{r:<5} {w:<6} {typ:<4} {en[:60]}')

    if '--private' in sys.argv:
        priv = sys.argv[sys.argv.index('--private') + 1]
        merged = merge(rows, os.path.join(priv, 'books/longtang/freq.tsv'))
        print('\nCombined ranking A + B (B = 《弄堂》, private; computed here, never written):')
        for n in (100, 300, 1000, 2000):
            part = [x for x in merged if x[0] <= n]
            got = sum(1 for x in part if x[1] in seen)
            print(f'  top {n:>4}: {got}/{len(part)} ({100 * got // max(1, len(part))}%)')
        missing = [x for x in merged if x[0] <= top and x[1] not in seen]
        missing.sort(key=lambda x: (x[2] not in ('sh', 'ff'), x[0]))
        print(f'\nNot taught yet, combined top {top} (Shanghainese words and false friends first; × = count in the novel):')
        for r, w, typ, c, en in missing[:50]:
            print(f'  #{r:<5} {w:<6} {typ:<4} {c:>4}×  {en[:55]}')


def merge(rows, freq_path):
    """One ranking from A (jieba carried to Shanghainese) and B (《弄堂》 counts). B weighs twice as much as A where the
    novel has the word at least 5 times; a word the novel lacks is pushed down; a Shanghainese word only the novel
    has (侪, 高头…) comes in with its novel rank. Returns [(rank, word, type, count, english)]."""
    import math
    b = {}
    for line in open(freq_path, encoding='utf8'):
        if line.startswith('#'):
            continue
        r, w, c, src, _ = (line.rstrip('\n').split('\t') + [''] * 5)[:5]
        if src == '-' or (src == 'mandarin' and len(w) > 1):
            continue                          # strings the splitter made up
        b[w] = (len(b) + 1, int(c), src)
    score, info = {}, {}
    for r, w, typ, say, en in rows:
        if typ in ('md', 'lit'):
            continue
        rb, c, _ = b.get(w, (None, 0, ''))
        score[w] = math.exp((2 * math.log(rb) + math.log(r)) / 3) if c >= 5 else r * 1.5
        info[w] = (typ, c, en)
    md = {x[1] for x in rows if x[2] in ('md', 'lit')}
    for w, (rb, c, src) in b.items():
        if w not in score and w not in md and c >= 10 and src in ('core', 'book', 'lexicon'):
            score[w] = rb * 1.2
            info[w] = ('sh' if src == 'book' else '?', c, '')
    order = sorted(score, key=score.get)
    return [(i, w, *info[w]) for i, w in enumerate(order, 1)]

if __name__ == '__main__':
    main()
