"""IPA is the reference form. Every other spelling is generated from it.

A syllable is stored as IPA with its citation tone as Chao numbers, e.g. "zɑ̃13".
From that we derive:
  - Wugniu (吴语学堂拼音), the spelling Wiktionary and most online material use
  - Qian Nairong's Shanghainese Pinyin (钱拼), the spelling of his printed dictionaries
    and textbooks, "new speakers" variant (əʔ and ᴀʔ both written -ak)
  - the spoken contour of a whole word (left-dominant tone sandhi)

The tables below are the only place the spelling systems are defined. If a book
spells something differently, the fix goes here (or in data/overrides.tsv for a
single word), never in the lessons.
"""
import re
import unicodedata

NFD = lambda x: unicodedata.normalize('NFD', x)

# citation tones of urban (new) Shanghainese, Chao numbers -> tone class used by Wugniu
TONES = {'53': 1, '34': 5, '334': 5, '13': 6, '113': 6, '55': 7, '5': 7, '12': 8}
CANON = {1: '53', 5: '34', 6: '13', 7: '55', 8: '12'}
TONE_NAME = {1: 'yin level', 5: 'yin departing', 6: 'yang', 7: 'yin entering', 8: 'yang entering'}
BAR = {'˥': '5', '˦': '4', '˧': '3', '˨': '2', '˩': '1'}

# left-dominant sandhi: the first syllable's tone class sets the melody of the whole word
SANDHI = {
    1: ['55 21', '55 33 21', '55 33 33 21', '55 33 33 33 21'],
    5: ['33 44', '33 55 21', '33 55 33 21', '33 55 33 33 21'],
    6: ['22 44', '22 55 21', '22 55 33 21', '22 55 33 33 21'],
    7: ['33 44', '33 55 21', '33 55 33 21', '33 55 33 33 21'],
    8: ['11 23', '11 22 23', '11 22 22 23', '11 22 22 22 23'],
}

INITIALS = ['ʦʰ', 'ʨʰ', 'pʰ', 'tʰ', 'kʰ', 'ʦ', 'ʨ', 'ʥ', 'p', 'b', 'm', 'f', 'v', 't', 'd', 'n', 'l',
            's', 'z', 'ɕ', 'ʑ', 'ȵ', 'k', 'g', 'ŋ', 'h', 'ɦ']
SYLLABIC = ['m̩', 'n̩', 'ŋ̩']

W_INIT = {'p': 'p', 'pʰ': 'ph', 'b': 'b', 'm': 'm', 'f': 'f', 'v': 'v', 't': 't', 'tʰ': 'th', 'd': 'd',
          'n': 'n', 'l': 'l', 'ʦ': 'ts', 'ʦʰ': 'tsh', 's': 's', 'z': 'z', 'ʨ': 'c', 'ʨʰ': 'ch', 'ʥ': 'j',
          'ɕ': 'sh', 'ʑ': 'zh', 'ȵ': 'gn', 'k': 'k', 'kʰ': 'kh', 'g': 'g', 'ŋ': 'ng', 'h': 'h', '': ''}
W_FIN = {'ɿ': 'y', 'i': 'i', 'u': 'u', 'y': 'iu', 'ᴀ': 'a', 'iᴀ': 'ia', 'uᴀ': 'ua', 'ᴇ': 'e', 'iᴇ': 'ie',
         'uᴇ': 'ue', 'ɔ': 'au', 'iɔ': 'iau', 'o': 'o', 'ø': 'oe', 'uø': 'uoe', 'yø': 'ioe', 'ɤ': 'eu',
         'iɤ': 'ieu', 'ã': 'an', 'iã': 'ian', 'uã': 'uan', 'ɑ̃': 'aon', 'iɑ̃': 'iaon', 'uɑ̃': 'uaon',
         'ən': 'en', 'in': 'in', 'uən': 'uen', 'yn': 'iun', 'oŋ': 'on', 'ioŋ': 'ion', 'ᴀʔ': 'aq',
         'iᴀʔ': 'iaq', 'uᴀʔ': 'uaq', 'əʔ': 'eq', 'uəʔ': 'ueq', 'oʔ': 'oq', 'ioʔ': 'ioq', 'iɪʔ': 'iq',
         'yɪʔ': 'iuq', 'əl': 'er', 'm̩': 'm', 'n̩': 'n', 'ŋ̩': 'ng'}

Q_INIT = {'p': 'b', 'pʰ': 'p', 'b': 'bh', 'm': 'm', 'f': 'f', 'v': 'fh', 't': 'd', 'tʰ': 't', 'd': 'dh',
          'n': 'n', 'l': 'l', 'ʦ': 'z', 'ʦʰ': 'c', 's': 's', 'z': 'sh', 'ʨ': 'j', 'ʨʰ': 'q', 'ʥ': 'jh',
          'ɕ': 'x', 'ʑ': 'xh', 'ȵ': 'ny', 'k': 'g', 'kʰ': 'k', 'g': 'gh', 'ŋ': 'ng', 'h': 'h', '': ''}
Q_FIN = {'ɿ': 'y', 'i': 'i', 'u': 'u', 'y': 'yu', 'ᴀ': 'a', 'iᴀ': 'ia', 'uᴀ': 'ua', 'ᴇ': 'e', 'iᴇ': 'ie',
         'uᴇ': 'ue', 'ɔ': 'ao', 'iɔ': 'iao', 'o': 'o', 'ø': 'oe', 'uø': 'uoe', 'yø': 'yuoe', 'ɤ': 'ou',
         'iɤ': 'iou', 'ã': 'ang', 'iã': 'iang', 'uã': 'uang', 'ɑ̃': 'ang', 'iɑ̃': 'iang', 'uɑ̃': 'uang',
         'ən': 'en', 'in': 'in', 'uən': 'uen', 'yn': 'yun', 'oŋ': 'ong', 'ioŋ': 'iong', 'ᴀʔ': 'ak',
         'iᴀʔ': 'iak', 'uᴀʔ': 'uak', 'əʔ': 'ak', 'uəʔ': 'uak', 'oʔ': 'ok', 'ioʔ': 'iok', 'iɪʔ': 'ik',
         'yɪʔ': 'yuik', 'əl': 'er', 'm̩': 'm', 'n̩': 'n', 'ŋ̩': 'ng'}

CHECKED = re.compile(r'ʔ$')
# compare in one Unicode form (ã can be one character or a + combining tilde)
for _t in ('W_FIN', 'Q_FIN'):
    globals()[_t] = {NFD(k): v for k, v in globals()[_t].items()}
SYLLABIC = [NFD(x) for x in SYLLABIC]


def from_bars(syl):
    """'zɑ̃˩˩˧' -> 'zɑ̃113'; a syllable with no tone mark keeps none (a toneless particle)."""
    s = re.sub(r'[˥˦˧˨˩]+', lambda m: ''.join(BAR[c] for c in m.group()), syl)
    return canonical(s)


def canonical(syl):
    """One way to write each tone: 113 -> 13, 334 -> 34, 5 -> 55 (so readings from different sources compare)."""
    syl = unicodedata.normalize('NFC', syl)
    m = re.match(r'^(.*?)(\d+)$', syl)
    if not m or m.group(2) not in TONES:
        return syl
    return m.group(1) + CANON[TONES[m.group(2)]]


def split(syl):
    """'zɑ̃113' -> ('z', 'ɑ̃', 6). Tone is None for a toneless particle."""
    syl = NFD(syl)
    m = re.match(r'^(.*?)(\d+)?$', syl)
    body, num = m.group(1), m.group(2)
    tone = TONES.get(num) if num else None
    if num and tone is None:
        raise ValueError(f'unknown tone {num} in {syl}')
    for s in SYLLABIC:
        if body.endswith(s) and body[:-len(s)] in ('', 'ɦ'):
            return body[:-len(s)], s, tone
    ini = next((i for i in INITIALS if body.startswith(i) and len(body) > len(i)), '')
    fin = body[len(ini):]
    if fin not in W_FIN:
        raise ValueError(f'unknown final {fin!r} in {syl}')
    return ini, fin, tone


def wugniu_syl(syl):
    ini, fin, _ = split(syl)
    f = W_FIN[fin]
    if ini == 'ɦ':
        if fin in SYLLABIC:
            return f                                   # 五 ng, 呒 m: Wugniu writes the yang tone only by number
        if fin == 'əl':
            return 'er'
        if f.startswith('i'):
            # 移 yi, 盐 yin, 叶 yiq keep the i; 羊 yan, 雨 yu, 有 yeu drop it
            return 'y' + f if len(f) == 1 or f[1] not in 'aeiouy' else 'y' + f[1:]
        if f.startswith('u'):
            return 'w' + (f[1:] or 'u')                # 胡 wu, 黄 waon
        return 'gh' + f                                # 鞋 gha
    return W_INIT[ini] + f


def _pinyin_zero(f):
    """Hanyu Pinyin's rules for a syllable with no consonant: i -> yi / y-, u -> wu / w-, ü -> yu."""
    if f.startswith('yu'):
        return f
    if f.startswith('i'):
        # i, in, ik keep their i (yi, yin, yik); ia, iao, iang drop it (ya, yao, yang)
        return 'y' + f if len(f) == 1 or f[1] not in 'aeiouy' else 'y' + f[1:]
    if f.startswith('u'):
        return 'w' + f if f == 'u' else 'w' + f[1:]
    return f


def qian_syl(syl):
    """Qian's 上海话拼音 as printed in his 《实用上海话词语手册》 (2011, rules pp. 9-16) and his course book."""
    ini, fin, _ = split(syl)
    f = Q_FIN[fin]
    if fin in SYLLABIC:
        return ('hh' if ini == 'ɦ' else '') + f       # 五 鱼 hhng, 吴 hhm (voiced); 姆 m, 呒 m
    if ini == 'ɦ':
        if f.startswith('yu'):
            return 'yh' + f[1:]                        # 雨 yhu, 园 yhuoe
        z = _pinyin_zero(f)
        if z[0] in 'yw' and z != f:
            return z[0] + 'h' + z[1:]                  # 洋 yhang, 黄 whang, 糊 whu
        return 'hh' + f                                # 闲 hhe, 话 hho
    if ini == '':
        return _pinyin_zero(f)
    if ini == 'ȵ':
        if f.startswith('yu'):
            return 'n' + f                             # 女 nyu, 软 nyuoe: ny only before yu
        if f.startswith('i'):
            return 'n' + _short(f)                     # 人 nin, 娘 niang, 日 nik, 牛 niu
    q = Q_INIT[ini] + (_short(f) if ini else f)
    if ini in ('ʨ', 'ʨʰ', 'ʥ', 'ɕ', 'ʑ') and f.startswith('yu'):
        q = Q_INIT[ini] + 'u' + f[2:]                  # 区 qu, 贵 ju, 血 xuik, 君 jun (the y drops after j q x)
    return q


def _short(f):
    """After an initial, iou and uen are written iu and un, as in Hanyu Pinyin: 救 jiu, 困 kun."""
    return {'iou': 'iu', 'uen': 'un'}.get(f, f)


def word(syls):
    """Everything the app shows for one word, from its IPA syllables (with Chao tone numbers)."""
    classes = [split(s)[2] for s in syls]
    first = next((c for c in classes if c), None)
    n = len(syls)
    if n == 1:
        contour = [CANON[first]] if first else ['']
    elif first:
        contour = SANDHI[first][min(n, 5) - 2].split()
        contour += contour[-1:] * (n - len(contour))
    else:
        contour = [''] * n
    return {
        'ipa': unicodedata.normalize('NFC', ' '.join(syls)),
        'wugniu': '-'.join(wugniu_syl(s) for s in syls),
        'qian': ''.join(qian_syl(s) for s in syls),
        'tone': first,                       # Wugniu tone class of the word (its first syllable)
        'tones': classes,                    # citation tone class of each syllable
        'contour': contour,                  # spoken pitch of each syllable inside this word
    }


if __name__ == '__main__':
    tests = {
        '上海人': 'zɑ̃113 hᴇ334 ȵin113', '白相': 'bᴀʔ12 ɕiã53', '洋': 'ɦiã113', '友': 'ɦiɤ113',
        '黄浦江': 'ɦuɑ̃113 pʰu334 kɑ̃53', '物事': 'məʔ12 zɿ113', '出洋相': 'ʦʰəʔ55 ɦiã113 ɕiã53',
        '拎勿清': 'lin53 vəʔ12 ʨʰin53', '淘浆糊': 'dɔ113 ʨiã53 ɦu113', '轧朋友': 'gəʔ12 bã113 ɦiɤ113',
        '五': 'ɦŋ̩113', '瀴': 'in53', '上海闲话': 'zɑ̃113 hᴇ334 ɦᴇ113 ɦo113', '谢谢侬': 'ʑiᴀ113 ʑiᴀ113 noŋ113',
        '女': 'ȵy113', '区': 'ʨʰy53', '血': 'ɕyɪʔ55', '救': 'ʨiɤ334', '困觉': 'kʰuən334 kɔ334',
    }
    # expected: Wugniu, Qian, word contour. The 8 Qian spellings marked * are the examples Qian published with his
    # input software; the rest freeze today's output, so a change to the rules shows up here (`make test`).
    expect = {
        '上海人': 'zaon-he-gnin shanghenin 22-55-21', '白相': 'baq-shian bhakxiang* 11-23',
        '洋': 'yan yhang 13', '友': 'yeu yhou 13', '黄浦江': 'waon-phu-kaon whangpugang* 22-55-21',
        '物事': 'meq-zy makshy* 11-23', '出洋相': 'tsheq-yan-shian cakyhangxiang* 33-55-21',
        '拎勿清': 'lin-veq-chin linfhakqin* 55-33-21', '淘浆糊': 'dau-cian-wu dhaojiangwhu* 22-55-21',
        '轧朋友': 'geq-ban-yeu ghakbhangyhou* 11-22-23', '五': 'ng hhng 13', '瀴': 'in yin 53',
        '上海闲话': 'zaon-he-ghe-gho shanghehhehho* 22-55-33-21', '谢谢侬': 'zhia-zhia-non xhiaxhianong 22-55-21',
        # rules of the handbook (pp. 12-13): ny only before yu; no y after j q x; iou -> iu, uen -> un
        '女': 'gniu nyu 13', '区': 'chiu qu 53', '血': 'shiuq xuik 55', '救': 'cieu jiu 34', '困觉': 'khuen-kau kungao 33-44',
    }
    import sys
    bad = 0
    for k, v in tests.items():
        w = word(v.split())
        got = f"{w['wugniu']} {w['qian']} {'-'.join(w['contour'])}"
        want = expect[k].replace('*', '')
        if '--test' in sys.argv:
            if got != want:
                bad += 1
                print(f'FAIL {k}: got {got}, want {want}')
        else:
            print(k, w['wugniu'], w['qian'], w['tone'], '-'.join(w['contour']))
    if '--test' in sys.argv:
        print('romanize:', 'ok' if not bad else f'{bad} failure(s)', f'({len(tests)} words)')
        sys.exit(1 if bad else 0)
