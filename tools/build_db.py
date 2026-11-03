"""Build the Shanghainese database and the app's data file.

Inputs (paths relative to the repo root):
  data/raw/zaonhe.txt     word -> IPA lexicon, ~150k entries (chinese-dialect-lexicons, built from Wugniu, MCPDict, rime-yahwe_zaonhe)
  data/raw/cedict_ts.u8   CC-CEDICT, for English glosses and Mandarin pinyin
  data/raw/jieba_dict.txt word frequencies (Mandarin web text), to rank words
  course/core.tsv          hand-written core words: type, gloss, Mandarin equivalent, corrected IPA
  course/overrides.tsv     corrections from checking books (word, IPA, book, note)
  course/lessons/*.yaml  the lessons

Outputs:
  data/build/lexicon.jsonl       every simplified-character word, with all spellings generated from IPA
  data/build/report.md           what the build had to guess (words composed character by character, etc.)
  app/build/data.js            what the app loads: lessons, the dictionary it needs, lesson 0, the bridge
"""
import json, re, sys, collections, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import romanize as R
import opencc
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
t2s = opencc.OpenCC('t2s').convert
report = collections.defaultdict(list)

# ---------- 1. the lexicon (IPA)
lex = {}
for line in open(ROOT / 'data/raw/zaonhe.txt', encoding='utf8'):
    w, p = line.rstrip('\n').split('\t')
    if t2s(w) != w:          # the file holds traditional and simplified twins; keep the simplified one
        continue
    syls = [R.from_bars(s) for s in p.split(' ')]
    if len(syls) != len(w):
        continue
    lex.setdefault(w, syls)

# ---------- 2. Mandarin: CC-CEDICT glosses, jieba frequency
cedict = {}
for line in open(ROOT / 'data/raw/cedict_ts.u8', encoding='utf8'):
    if line.startswith('#'):
        continue
    m = re.match(r'(\S+) (\S+) \[([^\]]+)\] /(.*)/', line)
    if not m:
        continue
    trad, simp, py, defs = m.groups()
    defs = re.sub(r'([^\s|/]+)\|[^\s\[/]+(\[[^\]]*\])?', r'\1', defs)       # 回來|回来[hui2 lai5] -> 回來
    defs = re.sub(r'\[[a-zA-Z0-9: ]+\]', '', defs)
    senses = [d.strip() for d in defs.split('/') if d and not d.startswith(('also pr', 'variant of', 'old variant', 'surname ', 'CL:', 'see '))]
    if senses and simp not in cedict:
        cedict[simp] = {'py': py, 'en': [x for x in senses if len(x) < 60][:3] or senses[:1]}

freq = {}
for line in open(ROOT / 'data/raw/jieba_dict.txt', encoding='utf8'):
    p = line.split()
    if len(p) >= 2:
        freq[p[0]] = int(p[1])
rank = {w: i + 1 for i, w in enumerate(sorted(freq, key=lambda w: -freq[w]))}

TONE_MARKS = {'1': '̄', '2': '́', '3': '̌', '4': '̀', '5': ''}
def pinyin_marks(py):
    out = []
    for s in py.split():
        m = re.match(r'([a-zA-Zü:]+)([1-5])$', s.replace('u:', 'ü'))
        if not m:
            out.append(s); continue
        syl, t = m.groups()
        i = next((syl.index(v) for v in 'aAeE' if v in syl), None)
        if i is None and 'ou' in syl: i = syl.index('o')
        if i is None: i = max(j for j, c in enumerate(syl) if c in 'aeiouüAEIOUÜ') if any(c in 'aeiouüAEIOUÜ' for c in syl) else None
        out.append(syl if i is None else syl[:i + 1] + TONE_MARKS[t] + syl[i + 1:])
    return ' '.join(out).lower() if py.islower() else ' '.join(out)

def mand(word):
    c = cedict.get(word)
    return {'py': pinyin_marks(c['py']), 'en': '; '.join(c['en'])} if c else None

# ---------- 3. core words and book corrections
def read_tsv(path, cols):
    rows = []
    if not path.exists():
        return rows
    for line in open(path, encoding='utf8'):
        if not line.strip() or line.startswith(('#', '!')):
            continue
        p = line.rstrip('\n').split('\t')
        rows.append(dict(zip(cols, p + [''] * (len(cols) - len(p)))))
    return rows

core = {r['word']: r for r in read_tsv(ROOT / 'course/core.tsv', ['word', 'type', 'en', 'zh', 'ipa', 'note'])}
overrides = {r['word']: r for r in read_tsv(ROOT / 'course/overrides.tsv', ['word', 'ipa', 'book', 'note'])}
for w, r in core.items():
    if r['type'] == 'auto':
        r['type'] = 'same' if w in cedict else 'sh'
verified = collections.defaultdict(list)
for r in read_tsv(ROOT / 'course/verified.tsv', ['word', 'ipa', 'book', 'date']):
    if r['word'] != 'word' and r['book']:
        verified[(r['word'], r['ipa'])].append(r['book'])

# ---------- traditional characters (the app shows simplified by default; Settings › Characters switches)
# OpenCC converts word by word; course/trad.tsv fixes what it gets wrong for Shanghainese (钟 → 鐘, not the surname 鍾).
S2T = opencc.OpenCC('s2t').convert
TRAD_FIX = sorted(((r['simp'], r['trad']) for r in read_tsv(ROOT / 'course/trad.tsv', ['simp', 'trad', 'note'])
                   if r['simp'] != 'simp' and len(r['simp']) == len(r['trad'])), key=lambda x: -len(x[0]))
def trad(s):
    t = S2T(s)
    if len(t) != len(s):
        return t
    t = list(t)
    for a, b in TRAD_FIX:
        i = s.find(a)
        while i >= 0:
            t[i:i + len(a)] = b
            i = s.find(a, i + 1)
    return ''.join(t)

def ipa_of(word, forced=None):
    """Reading of a word, best source first. Returns (syllables, source)."""
    if forced:
        return [R.canonical(x) for x in forced.split()], 'lesson'
    if word in overrides and overrides[word]['ipa']:
        return [R.canonical(x) for x in overrides[word]['ipa'].split()], 'book'
    if word in core and core[word]['ipa']:
        return [R.canonical(x) for x in core[word]['ipa'].split()], 'core'
    if word in lex:
        return lex[word], 'lexicon'
    # not in any list: put it together from its characters (the lexicon's single-character reading)
    syls = []
    for ch in word:
        r = ipa_of(ch)[0] if (ch in lex or ch in core or ch in overrides) else None
        if not r:
            return None, None
        syls += r
    return syls, 'composed'

def entry(word, forced=None):
    syls, src = ipa_of(word, forced)
    if not syls:
        return None
    e = {'h': word, **R.word(syls), 'src': src}
    if trad(word) != word: e['t'] = trad(word)
    c = core.get(word)
    if c:
        e.update(type=c['type'], gloss=c['en'], zh=[z for z in re.split('[、；;]', c['zh']) if z])
        if c['note']: e['note'] = c['note']
    elif word in cedict:
        e.update(type='same', gloss=mand(word)['en'])
    m = mand(word) or (mand(core[word]['zh'].split('、')[0]) if c and c['zh'] else None)
    if m: e['mand'] = m
    if word in overrides:
        e['book'] = {k: overrides[word][k] for k in ('book', 'note') if overrides[word][k]}
    if word in lex and src in ('core', 'book') and ' '.join(lex[word]) != e['ipa']:
        e['lexicon_ipa'] = ' '.join(lex[word])        # keep the lexicon's reading visible: the corrections stay checkable
    if verified.get((word, e['ipa'])): e['verified'] = sorted(set(verified[(word, e['ipa'])]))
    if word in rank: e['rank'] = rank[word]
    return e

# ---------- 4. full database
db_dir = ROOT / 'data/build'; db_dir.mkdir(exist_ok=True)
words = sorted(set(lex) | set(core), key=lambda w: (rank.get(w, 10 ** 7), w))
with open(db_dir / 'lexicon.jsonl', 'w', encoding='utf8') as f:
    for w in words:
        try:
            e = entry(w)
        except ValueError as err:
            report['unreadable'].append(f'{w}: {err}'); continue
        if e:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')

# ---------- 5. lessons
def parse_lesson(path):
    """course/lessons/NNN.yaml -> the shape the rest of this script uses"""
    y = yaml.safe_load(open(path, encoding='utf8'))
    L = {'title': f"{y['title']['hanzi']} | {y['title']['en']}", 'setting': y.get('setting', '').strip(),
         'review': 'yes' if y.get('review') else 'no',
         'lines': [{'speaker': d['speaker'], 'src': d['hanzi'], 'en': d['en'], 'lit': d.get('lit', '')} for d in y['dialogue']],
         'notes': [{'ref': nt['ref'], 'text': nt['text'].strip(), **({'topic': nt['topic']} if nt.get('topic') else {})}
                   for nt in y.get('notes', [])],
         'exercises': []}
    for kind, items in (y.get('exercises') or {}).items():
        for e in items:
            L['exercises'].append({'kind': {'translate': 'mean'}.get(kind, kind), 'src': e['hanzi'], 'en': e['en'],
                                   'answer': e.get('answer', '')})
    return L

dict_out = {}
HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')

def tokens(src, where):
    out = []
    for tok in src.split():
        m = re.match(r'^(.+?)\[(.+)\]$', tok)
        word, forced = (m.group(1), m.group(2).replace('_', ' ')) if m else (tok, None)
        if not HAN.search(word):
            out.append({'p': word} if re.fullmatch(r'[，。！？：、；…＿,.!?]+', word) else {'w': {'h': word}})
            continue
        e = entry(word, forced)
        if not e:
            report['missing'].append(f'{word} ({where})'); out.append({'w': {'h': word, **({'t': trad(word)} if trad(word) != word else {})}}); continue
        wid = f"{word}|{e['ipa']}"
        if wid not in dict_out:
            dict_out[wid] = e
            if e['src'] == 'composed': report['composed'].append(f"{word} → {e['wugniu']} ({where})")
            if 'gloss' not in e: report['no gloss'].append(f'{word} ({where})')
        out.append({'w': {'h': word, 'id': wid, **({'t': trad(word)} if trad(word) != word else {})}})
    return out

lessons = []
for p in sorted((ROOT / 'course/lessons').glob('[0-9][0-9][0-9].yaml')):
    L = parse_lesson(p)
    n = int(p.stem)
    seen, new_words = set(), []
    lines = []
    for i, ln in enumerate(L['lines']):
        toks = tokens(ln['src'], f'lesson {n} line {i + 1}')
        lines.append({'n': i + 1, 'speaker': ln['speaker'], 'en': ln['en'], 'lit': ln['lit'], 'tokens': toks})
        for t in toks:
            wid = t.get('w', {}).get('id')
            if wid and wid not in seen:
                seen.add(wid); new_words.append(wid)
    # new words: those not met in an earlier lesson
    earlier = set(w for l in lessons for w in l['all_words'])
    exercises = []
    for e in L['exercises']:
        exercises.append({'kind': e['kind'], 'tokens': tokens(e['src'], f'lesson {n} exercise'), 'en': e['en'],
                          'answer': e['answer'], 'answer_id': (tokens(e['answer'], 'answer')[0].get('w', {}).get('id') if e['answer'] and HAN.search(e['answer']) else None)})
    hz, en = [x.strip() for x in L['title'].split('|')]
    lessons.append({'id': n, 'title': {'hanzi': hz, 't': trad(hz), 'en': en, 'tokens': tokens(hz, f'lesson {n} title')},
                    'review': L.get('review') == 'yes', 'setting': L.get('setting', ''), 'lines': lines,
                    'notes': L['notes'], 'exercises': exercises, 'all_words': new_words,
                    'new_words': [w for w in new_words if w not in earlier]})
for l in lessons:
    del l['all_words']

# ---------- 6. dictionary for the app: lesson words + core + the most common words with a gloss
for w in core:
    e = entry(w)
    if e: dict_out.setdefault(f"{w}|{e['ipa']}", e)
common = [w for w in words if w in cedict and w in rank and rank[w] <= 20000 and len(w) <= 4][:6000]
for w in common:
    e = entry(w)
    if e: dict_out.setdefault(f"{w}|{e['ipa']}", e)

# ---------- 7. Mandarin bridge: frequent characters, the sound rule that links pinyin to Wugniu
def bridge_rules(py, e):
    """Plain-language rules that explain a Mandarin reading -> Shanghainese reading."""
    s, w = py.lower(), e['wugniu']
    ini, fin, tone = R.split(e['ipa'])
    rules = []
    if tone in (7, 8):
        rules.append('Ends in -q: an "entering tone" syllable, short and cut off by a glottal stop. Mandarin lost these endings, so the syllable is now in any Mandarin tone.')
    if ini in ('b', 'd', 'g', 'v', 'z', 'ʑ', 'ʥ', 'ɦ') and s[-1] in '24':
        rules.append('Mandarin tone 2 or 4 with a plain consonant often goes with a voiced, low-tone initial in Shanghainese (b, d, g, z, zh, j, v, gh): Middle Chinese kept a voiced consonant here.')
    if s.startswith(('zh', 'ch', 'sh')) and ini in ('ʦ', 'ʦʰ', 's', 'z'):
        rules.append('Mandarin zh / ch / sh → ts / tsh / s or z: Shanghainese has no retroflex consonants.')
    if s.startswith('r') and ini in ('z', 'ȵ'):
        rules.append('Mandarin r- → z- (literary) or gn- (colloquial, as in 人 gnin).')
    if s.startswith('w') and ini == 'v':
        rules.append('Mandarin w- → v- in many words (万 ve, 文 ven, 问 ven).')
    if re.match(r'^[a-z]*an[1-5]$', s) and not s.endswith(('ang1', 'ang2', 'ang3', 'ang4', 'ang5')) and fin in ('ᴇ', 'i', 'ø', 'uᴇ', 'yø', 'uø'):
        rules.append('Mandarin -an / -ian / -uan lost the n: Shanghainese -e, -i, -oe (三 se, 天 thi, 碗 uoe).')
    if s.startswith(('j', 'q', 'x')) and ini in ('ʦ', 'ʦʰ', 's', 'z'):
        rules.append('Mandarin j / q / x → ts / tsh / s here: an older split kept apart.')
    if not rules:
        rules.append('Close to the Mandarin reading once you know the spelling: compare the consonants and the vowel.')
    return rules

bridge, used = [], set()
singles = sorted([w for w in core if len(w) == 1] + [w for w in lex if len(w) == 1 and w in cedict and w in rank and rank[w] < 3000],
                 key=lambda w: rank.get(w, 10 ** 6))
pool = [entry(w) for w in dict.fromkeys(singles)]
pool = [e for e in pool if e and 'mand' in e]
for e in pool[:220]:
    if e['h'] in used: continue
    used.add(e['h'])
    ini, fin, tone = R.split(e['ipa'])
    near = {}
    for o in pool:
        if o['wugniu'] != e['wugniu'] and (R.split(o['ipa'])[0] == ini or R.split(o['ipa'])[1] == fin):
            near.setdefault(o['wugniu'], {'wugniu': o['wugniu'], 'qian': o['qian'], 'ipa': o['ipa']})
    opts = list(near.values())[:3]
    if len(opts) < 3: continue
    bridge.append({'char': e['h'], 'pinyin': e['mand']['py'], 'answer': {'wugniu': e['wugniu'], 'qian': e['qian'], 'ipa': e['ipa']},
                   'options': opts, 'rules': bridge_rules(cedict[e['h']]['py'] if e['h'] in cedict else '', e),
                   'meaning': e.get('gloss', e['mand']['en'])})

# ---------- 8. write
lesson0 = (ROOT / 'course/lessons/000-reading.html').read_text(encoding='utf8')
# character map for free text (notes, settings, Mandarin equivalents): one character at a time
_free = ''.join(l['setting'] + ''.join(x['text'] for x in l['notes']) for l in lessons) + ''.join(
    e['h'] + ''.join(e.get('zh', [])) + e.get('note', '') for e in dict_out.values())
_free += ''.join(x.read_text(encoding='utf8') for x in (ROOT / 'app/src').glob('*.js'))   # the app's own labels
s2t_map = {c: trad(c) for c in sorted(set(HAN.findall(_free))) if len(trad(c)) == 1 and trad(c) != c}
DATA = {'s2t': s2t_map, 'lessons': lessons, 'dict': dict_out, 'bridge': bridge, 'lesson0': lesson0,
        'built': datetime.date.today().isoformat(), 'tones': {str(k): {'contour': v, 'name': R.TONE_NAME[k], 'sandhi': R.SANDHI[k]} for k, v in R.CANON.items()}}
(ROOT / 'app/build').mkdir(parents=True, exist_ok=True)
def dump(d): return 'const DATA = ' + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + ';\n'
(ROOT / 'app/build/data.js').write_text(dump(DATA), encoding='utf8')

with open(db_dir / 'report.md', 'w', encoding='utf8') as f:
    f.write(f'# Build report ({DATA["built"]})\n\n')
    f.write(f'- lexicon: {len(words)} words · app dictionary: {len(dict_out)} words · lessons: {len(lessons)} · bridge: {len(bridge)} characters\n\n')
    for k, v in report.items():
        f.write(f'## {k} ({len(v)})\n\n' + '\n'.join(f'- {x}' for x in v[:400]) + '\n\n')
print(open(db_dir / 'report.md', encoding='utf8').read()[:3000])
