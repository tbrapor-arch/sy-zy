"""Word cutting and word tokens: the one copy, shared by the public build (tools/build_db.py) and the private
module (syzy-private/tools/build_module.py). Change the shape of a token or the cutting rules here only.

A text line is written with spaces between words, as in the lessons:
    侬 是 新[ɕin53] 来 个 伐 ？
  - 字[IPA] forces a reading for this occurrence (syllables joined by _);
  - ~字 is a sung syllable that is not a word (shown, no card);
  - punctuation and Latin words pass through.
"""
import pathlib
import re

HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')
PUNCT = re.compile(r'^[，。！？：、；…＿,.!?“”‘’"「」『』（）()《》—\-·]+$')
FORCED = re.compile(r'^(.+?)\[(.+)\]$')


def split(src):
    """Cut a line into ('p', text) punctuation, ('plain', text) a non-Chinese word or a chant syllable,
    and ('word', word, forced) a Chinese word with its forced reading (raw, with _) or None."""
    for tok in src.split():
        if tok.startswith('~') and len(tok) > 1:
            yield ('plain', tok[1:])
            continue
        m = FORCED.match(tok)
        word, forced = (m.group(1), m.group(2)) if m else (tok, None)
        if PUNCT.match(word):
            yield ('p', word)
        elif not HAN.search(word):
            yield ('plain', word)
        else:
            yield ('word', word, forced)


def load_trad(root):
    """Simplified -> traditional: OpenCC word by word, then course/trad.tsv for what it gets wrong in Shanghainese."""
    import opencc
    s2t = opencc.OpenCC('s2t').convert
    fix = []
    for line in open(pathlib.Path(root) / 'course/trad.tsv', encoding='utf8'):
        if not line.strip() or line.startswith(('#', '!')):
            continue
        p = line.rstrip('\n').split('\t')
        if len(p) >= 2 and p[0] != 'simp' and len(p[0]) == len(p[1]):
            fix.append((p[0], p[1]))
    fix.sort(key=lambda x: -len(x[0]))

    def trad(s):
        t = s2t(s)
        if len(t) != len(s):
            return t
        t = list(t)
        for a, b in fix:
            i = s.find(a)
            while i >= 0:
                t[i:i + len(a)] = b
                i = s.find(a, i + 1)
        return ''.join(t)
    return trad


def compose(word, reading):
    """A word no list has, put together from its characters. reading(ch) -> list of IPA syllables or None.
    Every such reading is a guess until a dictionary confirms it (the build report lists them)."""
    syls = []
    for ch in word:
        r = reading(ch)
        if not r:
            return None
        syls += r
    return syls


def token(word, e, trad):
    """The token a line carries for a word: headword, card id (word|IPA) when it has a reading, traditional form."""
    t = e.get('t') if e else None
    t = t or (trad(word) if trad(word) != word else None)
    w = {'h': word}
    if e:
        w['id'] = f"{word}|{e['ipa']}"
    if t:
        w['t'] = t
    return {'w': w}
