"""One packet per lesson: everything the writer needs for lesson N, in one file.

  python3 tools/packet.py 50                       # -> data/build/packets/050.md (not committed)
  python3 tools/packet.py 50 --private ../syzy-private

The packet holds: the syllabus entry; the curve targets (tools/lint.py); the target words with reading, source of the
reading, type and gloss; warnings (reading composed and unchecked, no gloss, a character read differently from a word
already taught); words of earlier lessons met in one dialogue line only, to bring back; the grammar taught so far.
With --private (the owner's private repo): each word's rank in the private master list, its count in 《弄堂》, and
up to three lines from the private books showing how it is used. Those lines inform the writer: they are never copied
into a lesson and the packet is never committed (rule 1 of course/README.md: every sentence is original).
Run `make db` first.
"""
import glob, os, re, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import lint, plan_check

HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')


def tokens(text):
    return [re.sub(r'\[[^\]]*\]$', '', t) for t in text.split() if HAN.search(t)]


def written(before):
    """Lessons already written, below `before`: per word, the lessons and number of dialogue lines it is in."""
    lines, first, grammar = {}, {}, []
    for p in sorted(glob.glob(os.path.join(ROOT, 'course/lessons/[0-9][0-9][0-9].yaml'))):
        y = yaml.safe_load(open(p, encoding='utf8'))
        if y['id'] >= before:
            continue
        for d in y['dialogue']:
            for w in set(tokens(d['hanzi'])):
                lines[w] = lines.get(w, 0) + 1
                first.setdefault(w, y['id'])
        for w in y.get('new_words') or []:
            first.setdefault(w['hanzi'].split('[')[0], y['id'])
    return lines, first


def char_readings(first, lex):
    """character -> {syllable without tone: (word, lesson)} over the words already taught"""
    out = {}
    for w, n in first.items():
        e = lex.get(w)
        if not e:
            continue
        syls = e['ipa'].split()
        if len(syls) != len(w):
            continue
        for ch, s in zip(w, syls):
            out.setdefault(ch, {}).setdefault(re.sub(r'\d+$', '', s), (w, n))
    return out


def private_info(priv, words):
    info = {w: {'rank': '', 'hb': '', 'lt': 0, 'ex': []} for w in words}
    p = os.path.join(priv, 'vocab/master.tsv')
    if os.path.exists(p):
        for line in open(p, encoding='utf8'):
            c = line.rstrip('\n').split('\t')
            if not line.startswith('#') and c[1] in info:
                info[c[1]]['rank'] = c[0]
                info[c[1]]['hb'] = c[13] if len(c) > 13 else ''
    p = os.path.join(priv, 'books/longtang/freq.tsv')
    if os.path.exists(p):
        for line in open(p, encoding='utf8'):
            c = line.rstrip('\n').split('\t')
            if not line.startswith('#') and len(c) > 2 and c[1] in info:
                info[c[1]]['lt'] = int(c[2])

    def see(src, text, toks, en):
        for w in set(toks.split()) & set(info):
            if len(info[w]['ex']) < 3 and not any(x[0] == src for x in info[w]['ex']):
                info[w]['ex'].append((src, text, en))
    for f in sorted(glob.glob(os.path.join(priv, 'books/longtang/ch*.yaml'))):
        for para in yaml.safe_load(open(f, encoding='utf8')).get('paras') or []:
            for l in para.get('l') or []:
                if len(l) > 2: see('弄堂', l[0], l[1], l[2])
    for f in sorted(glob.glob(os.path.join(priv, 'coursebooks/*/[0-9][0-9]/lesson.yaml'))):
        for sc in yaml.safe_load(open(f, encoding='utf8')).get('scenes') or []:
            for l in sc.get('lines') or []:
                see('钱乃荣', l.get('o', ''), l.get('w', ''), l.get('en', ''))
    for f in sorted(glob.glob(os.path.join(priv, 'bookcourse/[0-9][0-9]/lesson.yaml'))):
        for l in yaml.safe_load(open(f, encoding='utf8')).get('lines') or []:
            if isinstance(l, list) and len(l) > 3: see('丁迪蒙', l[1], l[2], l[3])
    return info


def main():
    args = [a for a in sys.argv[1:] if a.isdigit()]
    if not args:
        sys.exit(__doc__)
    n = int(args[0])
    priv = sys.argv[sys.argv.index('--private') + 1] if '--private' in sys.argv else None
    syl = {e['n']: e for e in yaml.safe_load(open(os.path.join(ROOT, 'course/syllabus.yaml'), encoding='utf8'))['lessons']}
    e = syl[n]
    lex = plan_check.load_lexicon()
    lines, first = written(n)
    known = char_readings(first, lex)
    words = e.get('words') or []
    out = [f"# Packet for lesson {n}: {e.get('hanzi', '')} · {e['en']}", '']
    if priv:
        out += ['**Private packet: holds lines from the owner\'s books. Never commit it, never copy a line into a lesson.**', '']
    out += ['## Syllabus', f"- Setting: {e.get('setting', '(none)')}", f"- Focus: {e.get('focus', '(none)')}"]
    if e.get('review'):
        prev = [syl[k] for k in range(n - 6, n) if k in syl]
        out += ['- Review lesson: no new words. Bring back the words and grammar of ' + ', '.join(f"L{p['n']} ({p['en']})" for p in prev)]
    out += ['', '## Targets (tools/lint.py)',
            f'- Lines: {lint.target_lines(n)}' + (' (numbered sentences: narrated lesson)' if n >= 85 else ''),
            f'- Median syllables per line: {lint.target_syllables(n)} (±1)',
            f'- New words: {lint.target_new_words(n)}' + (' (±2)' if not e.get('review') else ''),
            '- Exercises: 3 translate + 3 fill + 3 say, none copied from a dialogue line, only words already met', '']
    warn = []
    if words:
        info = private_info(priv, words) if priv else None
        out += ['## Target words', '', '| word | Qian | IPA | reading from | type | gloss |' + (' master rank | 弄堂 |' if priv else ''),
                '|---|---|---|---|---|---|' + ('---|---|' if priv else '')]
        for w in words:
            q, ipa, src, gloss, typ = plan_check.reading(w, lex)
            extra = f" {info[w]['rank']}{' · ' + info[w]['hb'] if info[w]['hb'] else ''} | {info[w]['lt'] or ''} |" if priv else ''
            out.append(f'| {w} | {q} | {ipa} | {src} | {typ} | {gloss} |{extra}')
            if src == 'composed':
                warn.append(f'{w}: reading composed character by character ({ipa}), not checked. Check it (a dictionary, '
                            'wugniu.com, Wiktionary), then give it a reading in course/core.tsv. Lint refuses it otherwise.')
            if src == 'none':
                warn.append(f'{w}: a character has no reading. Give the word one in course/core.tsv.')
            if not gloss:
                warn.append(f'{w}: no English gloss. Add it to course/core.tsv.')
            syls = ipa.split()
            if len(syls) == len(w):
                for ch, s in zip(w, syls):
                    s0 = re.sub(r'\d+$', '', s)
                    if ch in known and s0 not in known[ch]:
                        ow, on = next(iter(known[ch].values()))
                        warn.append(f'{w}: 字 {ch} is read {s0} here, but {" / ".join(known[ch])} in {ow} (lesson {on}). '
                                    'Right? If so, a note should say it.')
        out += ['', '## Warnings'] + ([f'- {x}' for x in warn] or ['- None.']) + ['']
        if priv:
            out += ['## How the private books use these words (to inform, never to copy)']
            for w in words:
                for src, text, en in info[w]['ex']:
                    out.append(f'- **{w}** · {src}: {text} — {en}')
            out.append('')
    # words to bring back: met in one dialogue line only; those sharing a character with this lesson first
    here = set(''.join(words) + e.get('hanzi', ''))
    once = [w for w, k in lines.items() if k == 1 and len(w) > 1]
    once.sort(key=lambda w: (not (set(w) & here), first.get(w, 0)))
    out += ['## Words to bring back (in one dialogue line so far; the first ones share a character with this lesson)',
            ' · '.join(f'{w} (L{first.get(w, "?")})' for w in once[:14]) or '(none)', '']
    done = [syl[k] for k in sorted(syl) if k < n and syl[k].get('focus')]
    out += ['## Grammar of the last lessons (do not re-teach; reuse)'] + [f"- L{p['n']}: {p['focus']}" for p in done[-8:]] + ['']
    out += ['## Before you write', '- Read course/README.md (the rules), course/card.md (review findings) and course/state.md (cast, story).',
            '- Then: `make db lint`, fix every error, fix or justify every warning; add two lines to course/state.md.', '']
    d = os.path.join(ROOT, 'data/build/packets'); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f'{n:03d}.md')
    open(path, 'w', encoding='utf8').write('\n'.join(out))
    print(path, f'· {len(words)} words · {len(warn)} warnings')


if __name__ == '__main__':
    main()
