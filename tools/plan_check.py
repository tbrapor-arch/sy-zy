"""Check the words planned for lessons 50–100 once, before the lessons are written.

  python3 tools/plan_check.py            # -> data/build/plan_check.tsv + a summary (run `make db` first)
  python3 tools/plan_check.py 50 56      # only lessons 50–56, printed

For each target word of course/syllabus.yaml: lesson, word, Qian pinyin, IPA, source of the reading, type, gloss, flags.
Source: book (course/overrides.tsv) · core (course/core.tsv) · lexicon · checked (composed, and course/verified.tsv
confirms that reading) · composed (put together character by character: can be wrong, 文读/白读) · none (a character
has no reading). Flags: composed, no-reading, no-gloss, taught
(already a new word of a written lesson), twice (planned in two lessons).
tools/lint.py refuses a new word with a composed reading from lesson 50 on: give it a reading in course/core.tsv
(or course/overrides.tsv when a book confirms it), or force it in the lesson with 字[IPA].
"""
import glob, json, os, re, sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romanize as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_lexicon():
    lex = {}
    p = os.path.join(ROOT, 'data/build/lexicon.jsonl')
    if not os.path.exists(p):
        raise FileNotFoundError('data/build/lexicon.jsonl is missing: run `make db` first')
    for line in open(p, encoding='utf8'):
        e = json.loads(line)
        lex.setdefault(e['h'], e)
    return lex


def tsv(name, cols):
    out = {}
    for line in open(os.path.join(ROOT, 'course', name), encoding='utf8'):
        if line.strip() and not line.startswith(('#', '!')):
            p = line.rstrip('\n').split('\t')
            out[p[0]] = dict(zip(cols, p + [''] * (len(cols) - len(p))))
    return out


def cedict():
    out = {}
    for line in open(os.path.join(ROOT, 'data/raw/cedict_ts.u8'), encoding='utf8'):
        m = re.match(r'(\S+) (\S+) \[[^\]]+\] /(.*)/', line)
        if m and m.group(2) not in out:
            out[m.group(2)] = m.group(3).split('/')[0]
    return out


OVER = tsv('overrides.tsv', ['word', 'ipa', 'book', 'note'])
CORE = tsv('core.tsv', ['word', 'type', 'en', 'zh', 'ipa', 'note'])
VERIFIED = set()
for _l in open(os.path.join(ROOT, 'course/verified.tsv'), encoding='utf8'):
    _p = _l.rstrip('\n').split('\t')
    if len(_p) > 2 and not _l.startswith('#'):
        VERIFIED.add((_p[0], _p[1]))
CEDICT = None


def reading(word, lex):
    """(qian, ipa, source, gloss, type) of a word, as tools/build_db.py reads it."""
    global CEDICT
    CEDICT = CEDICT or cedict()
    c = CORE.get(word, {})
    gloss = c.get('en') or CEDICT.get(word, '')
    typ = c.get('type') or ('same' if word in CEDICT else '')
    if OVER.get(word, {}).get('ipa'):
        w = R.word([R.canonical(x) for x in OVER[word]['ipa'].split()])
        return w['qian'], w['ipa'], 'book', gloss, typ
    e = lex.get(word)
    if e:
        src = 'checked' if e['src'] == 'composed' and (word, e['ipa']) in VERIFIED else e['src']
        return e['qian'], e['ipa'], src, e.get('gloss', gloss), e.get('type', typ)
    syls = []
    for ch in word:
        x = lex.get(ch)
        if not x:
            return '', '', 'none', gloss, typ
        syls += x['ipa'].split()
    w = R.word(syls)
    return w['qian'], w['ipa'], 'checked' if (word, w['ipa']) in VERIFIED else 'composed', gloss, typ


def taught_words():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'course/lessons/[0-9][0-9][0-9].yaml'))):
        y = yaml.safe_load(open(p, encoding='utf8'))
        for w in y.get('new_words') or []:
            out.setdefault(w['hanzi'].split('[')[0], y['id'])
    return out


def rows(lo=50, hi=100):
    lex, taught = load_lexicon(), taught_words()
    plan = [(e['n'], w) for e in yaml.safe_load(open(os.path.join(ROOT, 'course/syllabus.yaml'), encoding='utf8'))['lessons']
            for w in e.get('words') or []]
    count = {}
    for _, w in plan:
        count[w] = count.get(w, 0) + 1
    out = []
    for n, w in plan:
        if not lo <= n <= hi:
            continue
        q, ipa, src, gloss, typ = reading(w, lex)
        flags = [f for f, on in (('composed', src == 'composed'), ('no-reading', src == 'none'), ('no-gloss', not gloss),
                                 ('taught', w in taught and taught[w] < n), ('twice', count[w] > 1)) if on]
        out.append(dict(n=n, word=w, qian=q, ipa=ipa, src=src, type=typ, gloss=gloss, flags=' '.join(flags)))
    return out


def main():
    args = [int(a) for a in sys.argv[1:] if a.isdigit()]
    lo, hi = (args + [100, 100])[:2] if args else (50, 100)
    if len(args) == 1:
        hi = lo
    rs = rows(lo, hi)
    cols = ['n', 'word', 'qian', 'ipa', 'src', 'type', 'gloss', 'flags']
    if args:
        for r in rs:
            print('\t'.join(str(r[c]) for c in cols))
    else:
        with open(os.path.join(ROOT, 'data/build/plan_check.tsv'), 'w', encoding='utf8') as o:
            o.write('# Words planned for lessons 50–100 (course/syllabus.yaml), as the build reads them. tools/plan_check.py\n')
            o.write('\t'.join(cols) + '\n')
            for r in rs:
                o.write('\t'.join(str(r[c]) for c in cols) + '\n')
    n = len(rs)
    print(f'{n} planned words: ' + ' · '.join(f'{sum(1 for r in rs if k in r["flags"].split())} {k}'
                                              for k in ('composed', 'no-reading', 'no-gloss', 'taught', 'twice')))


if __name__ == '__main__':
    main()
