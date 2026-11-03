"""The common-vocabulary list: the words a learner meets most, ranked, as Tsheh-tû's core list (step A).

  python3 tools/core_vocab.py        # -> data/build/core_vocab.tsv

There is no frequency list of spoken Shanghainese, so the rank comes from Mandarin (jieba) and is carried over to the
Shanghainese word wherever Shanghainese says it differently: the rank of 你 goes to 侬, 在 to 辣, 什么 to 啥, 东西 to
物事 (the "mandarin" column of course/core.tsv). The Mandarin word stays in the list, typed md and pointing to the
Shanghainese one, and is never taught for itself. Step B (the owner's books, private) can re-rank later:
tools/coverage.py --private.

Columns: rank, word, type (sh Shanghainese word · ff false friend · same · md Mandarin word, see "say" ·
lit written Mandarin, hardly said), say, english.
Only words with a Shanghainese reading in the lexicon (or in core.tsv) and an entry in CC-CEDICT are kept.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 3000
# Written Mandarin: frequent in jieba's (written) corpus, hardly ever said in Shanghainese. Typed lit, never taught.
LITERARY = set('之 而 与 以 于 将 其 及 则 亦 乃 该 此 均 即 且 某 皆 遂 尚 至 所 被 并 为 由 向 曾 已 仍 各 凡 若'.split())

def main():
    lex = set()
    for line in open(os.path.join(ROOT, 'data/raw/zaonhe.txt'), encoding='utf8'):
        lex.add(line.split('\t')[0])
    cedict = {}
    for line in open(os.path.join(ROOT, 'data/raw/cedict_ts.u8'), encoding='utf8'):
        m = re.match(r'(\S+) (\S+) \[[^\]]+\] /(.*)/', line)
        if m and m.group(2) not in cedict:
            senses = [s for s in m.group(3).split('/') if s and not s.startswith(('variant of', 'old variant', 'surname', 'CL:', 'see ', 'also pr'))]
            cedict[m.group(2)] = senses
    freq = {}
    for line in open(os.path.join(ROOT, 'data/raw/jieba_dict.txt'), encoding='utf8'):
        p = line.split()
        if len(p) >= 2:
            freq[p[0]] = int(p[1])
    rank = {w: i + 1 for i, w in enumerate(sorted(freq, key=lambda w: -freq[w]))}

    core, says = {}, {}
    for line in open(os.path.join(ROOT, 'course/core.tsv'), encoding='utf8'):
        if line.startswith('#') or not line.strip():
            continue
        p = (line.rstrip('\n').split('\t') + [''] * 6)[:6]
        word, typ, en, zh = p[:4]
        core[word] = (typ, en)
        if typ in ('sh', 'ff'):
            for m in re.split(r'[、；;]', re.sub(r'（[^）]*）', '', zh)):
                m = m.strip()
                if m and m != word:
                    says.setdefault(m, []).append(word)
    for m in list(says):
        if m in core:               # also an everyday Shanghainese word (好, 跟…): it keeps its own place
            del says[m]

    def proper_noun(w):
        s = cedict.get(w) or ['']
        return bool(re.match(r'[A-Z]', s[0])) and not any(re.match(r'[a-z(]', x) for x in s)

    out, placed = [], set()

    def add(w, r, typ, say=''):
        if w in placed:
            return
        placed.add(w)
        en = core[w][1] if w in core else '; '.join((cedict.get(w) or [''])[:2])
        out.append([r, w, typ, say, en[:80]])

    for w in sorted(rank, key=rank.get):
        if len(out) >= SIZE:
            break
        if len(w) > 4 or not re.fullmatch(r'[㐀-鿿]+', w):
            continue
        r = rank[w]
        if w in says:                       # Mandarin word Shanghainese replaces: its rank goes to the Shanghainese word
            for s in says[w]:
                add(s, r, core[s][0])
            if w not in core and w in cedict:
                add(w, r, 'md', '、'.join(says[w]))
            continue
        if w in core:
            add(w, r, core[w][0])
        elif w in LITERARY:
            add(w, r, 'lit')
        elif w in cedict and w in lex and not proper_noun(w):
            add(w, r, 'same')
    # core words no Mandarin rank reached: put them after, in file order (they were picked by hand as everyday words)
    for w, (typ, _) in core.items():
        if w not in placed:
            add(w, SIZE_TAIL + len(out), typ)

    out.sort(key=lambda x: x[0])
    path = os.path.join(ROOT, 'data/build/core_vocab.tsv')
    with open(path, 'w', encoding='utf8') as f:
        f.write('# Common vocabulary (step A: jieba ranks carried to the Shanghainese word). Built by tools/core_vocab.py.\n')
        f.write('# rank\tword\ttype\tsay\tenglish\n')
        for i, (_, w, typ, say, en) in enumerate(out, 1):
            f.write(f'{i}\t{w}\t{typ}\t{say}\t{en}\n')
    n_md = sum(1 for x in out if x[2] == 'md')
    print(f'{path}: {len(out)} words ({n_md} Mandarin words pointing to their Shanghainese equivalent)')


SIZE_TAIL = 10 ** 6

if __name__ == '__main__':
    main()
