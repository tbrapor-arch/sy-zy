"""Check the lessons: schema, and the L1–50 progression decided in the plan (by number of lines).

  python3 tools/lint.py            # schema errors fail; curve differences are warnings
  python3 tools/lint.py --strict   # curve differences fail too (use once a lesson is final)

Curve (docs/course-plan.md §3):
  lines     6 at L1–5, +1 every 5 lessons → 15 at L46–50; a review lesson has 2 fewer lines
  syllables median per line: 7 (L1–10), 8, 9, 10, 11 (L41–50); more than 1 syllable off = warning
  new words 12 → 20, linear (±2); review lessons: none
  exercises 5 translate + 3 fill
"""
import glob, os, re, statistics, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')
PUNCT = re.compile(r'^[，。！？：、；…＿,.!?“”"「」（）()]+$')


def is_review(n):
    return n % 7 == 0


def target_lines(n):
    lines = 6 + (n - 1) // 5          # L1–5: 6, L6–10: 7 … L46–50: 15
    return lines - 2 if is_review(n) else lines


def target_syllables(n):
    return 7 + (n - 1) // 10           # L1–10: 7 … L41–50: 11


def target_new_words(n):
    return 0 if is_review(n) else round(12 + (n - 1) * 8 / 49)


def syllables(text):
    """Han characters + Latin words; a forced reading 字[IPA] counts as its characters."""
    text = re.sub(r'\[[^\]]*\]', '', text)
    n = 0
    for tok in text.split():
        if PUNCT.match(tok):
            continue
        han = len(HAN.findall(tok))
        n += han if han else 1
    return n


def check(path, strict):
    errors, warns = [], []
    y = yaml.safe_load(open(path, encoding='utf8'))
    n = y.get('id')
    for k in ('id', 'title', 'dialogue'):
        if k not in y:
            errors.append(f'missing "{k}"')
    if errors:
        return n, errors, warns
    if int(os.path.basename(path)[:3]) != n:
        errors.append(f'id {n} does not match the file name')
    if not {'en', 'hanzi'} <= set(y['title']):
        errors.append('title needs en and hanzi')
    if bool(y.get('review')) != is_review(n):
        errors.append(f'review should be {is_review(n)} (a review every 7 lessons)')
    for i, d in enumerate(y['dialogue'], 1):
        for k in ('n', 'speaker', 'hanzi', 'en'):
            if k not in d:
                errors.append(f'line {i}: missing "{k}"')
        if d.get('n') != i:
            errors.append(f'line {i}: n is {d.get("n")}')
        for m in re.finditer(r'(\S+?)\[([^\]]*)\]', d.get('hanzi', '')):
            word, ipa = m.groups()
            if len(ipa.split('_')) != len(HAN.findall(word)):
                errors.append(f'line {i}: {word}[{ipa}] has {len(HAN.findall(word))} characters but {len(ipa.split("_"))} syllables')
    lines = len(y['dialogue'])
    for nt in y.get('notes', []):
        if not 1 <= nt.get('ref', 0) <= lines:
            errors.append(f'note refers to line {nt.get("ref")}')

    if n <= 50:
        want = target_lines(n)
        if lines != want:
            warns.append(f'{lines} lines, curve says {want}')
        med = statistics.median(syllables(d['hanzi']) for d in y['dialogue'])
        if abs(med - target_syllables(n)) > 1:
            warns.append(f'median {med:g} syllables per line, curve says {target_syllables(n)}')
        ex = y.get('exercises') or {}
        if len(ex.get('translate', [])) != 5 or len(ex.get('fill', [])) != 3:
            warns.append(f'exercises: {len(ex.get("translate", []))} translate + {len(ex.get("fill", []))} fill, want 5 + 3')
    if strict:
        errors += warns
        warns = []
    return n, errors, warns


def main():
    strict = '--strict' in sys.argv
    bad = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'course/lessons/[0-9][0-9][0-9].yaml'))):
        n, errors, warns = check(p, strict)
        for e in errors:
            print(f'L{n}: ERROR {e}')
        for w in warns:
            print(f'L{n}: warning {w}')
        bad += bool(errors)
    print('lint:', 'ok' if not bad else f'{bad} lesson(s) with errors')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
