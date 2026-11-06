"""Synthetic Shanghainese audio for the lesson dialogues: course/lessons/NNN.yaml -> audio/NNN/LL.mp3

Voices: Microsoft's Wu Chinese (Shanghainese) neural voices, wuu-CN-XiaotongNeural (female) and
wuu-CN-YunzheNeural (male). They exist only on the Azure Speech API: the free Edge "Read aloud" endpoint
(speech.platform.bing.com) does not carry them (checked 6 Nov 2026; its Chinese voices are Mandarin,
Liaoning, Shaanxi, Hong Kong Cantonese and Taiwan Mandarin). The free Azure tier (F0) gives 500,000
characters a month, far more than the course needs.

  AZURE_SPEECH_KEY=… AZURE_SPEECH_REGION=eastasia python3 tools/tts.py          # new or changed lines only
  python3 tools/tts.py --lesson 3 --force                                       # one lesson, again
  python3 tools/tts.py --dry-run                                                # what would be sent
  python3 tools/tts.py --backend edge --female zh-HK-HiuMaanNeural …            # Edge, for the voices it has

Who speaks with which voice: course/voices.tsv (speaker <TAB> female|male). A speaker not listed gets the
female voice if they speak first in the lesson, the male voice otherwise.

The voice reads characters with its own readings: it does not see the lesson's IPA (新[ɕin53]). When it
reads a word wrongly, put a respelling in course/tts_fix.tsv (word <TAB> what to send instead), usually a
homophone, and run again: only the lines that change are made again.

audio/index.json records, per line, the text sent and a hash of (voice, rate, text). build_db.py gives a line
its audio only when that text still matches the lesson, so an edited line goes silent until it is made again.
"""
import argparse, asyncio, hashlib, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'audio'
INDEX = OUT / 'index.json'
VOICES = {'female': 'wuu-CN-XiaotongNeural', 'male': 'wuu-CN-YunzheNeural'}
LOCALE = 'wuu-CN'
FORMAT = 'audio-24khz-48kbitrate-mono-mp3'


def tsv(path):
    p = ROOT / path
    if not p.exists():
        return {}
    out = {}
    for ln in p.read_text(encoding='utf8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            k, v = ln.split('\t')[:2]
            out[k.strip()] = v.strip()
    return out


def spoken(hanzi, fixes):
    """lesson hanzi (words split by spaces, forced readings in brackets) -> the text the voice reads"""
    words = []
    for tok in hanzi.split():
        w = re.sub(r'\[.*\]$', '', tok)
        words.append(fixes.get(w, w))
    text = ''
    for w in words:  # keep a space only between two Latin words (Sam, OK…)
        if text and re.search(r'[A-Za-z0-9]$', text) and re.match(r'[A-Za-z0-9]', w):
            text += ' '
        text += w
    return text


def ssml(text, voice, rate):
    body = escape(text)
    if rate:
        body = f'<prosody rate="{rate}">{body}</prosody>'
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{LOCALE}">'
            f'<voice name="{voice}">{body}</voice></speak>')


def azure(text, voice, rate):
    key, region = os.environ.get('AZURE_SPEECH_KEY'), os.environ.get('AZURE_SPEECH_REGION')
    if not key or not region:
        sys.exit('tts.py: set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION (Azure portal › Speech service › Keys and Endpoint)')
    req = urllib.request.Request(
        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml(text, voice, rate).encode('utf8'), method='POST',
        headers={'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml',
                 'X-Microsoft-OutputFormat': FORMAT, 'User-Agent': 'syzy-tts'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:  # free tier: 20 requests a minute
                time.sleep(int(e.headers.get('Retry-After') or 10)); continue
            msg = e.read().decode('utf8', 'replace')[:200]
            sys.exit(f'tts.py: Azure said {e.code} {msg} (is {voice} offered in region {region}?)')


def edge(text, voice, rate):
    import edge_tts, ssl  # pip install edge-tts
    if os.environ.get('SSL_CERT_FILE'):  # behind a proxy with its own certificate
        import edge_tts.communicate as ec
        ec._SSL_CTX = ssl.create_default_context(cafile=os.environ['SSL_CERT_FILE'])
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    async def go():
        buf = b''
        async for c in edge_tts.Communicate(text, voice, rate=rate or '+0%', proxy=proxy).stream():
            if c['type'] == 'audio':
                buf += c['data']
        return buf
    try:
        data = asyncio.run(go())
    except edge_tts.exceptions.NoAudioReceived:
        data = b''
    if not data:
        sys.exit(f'tts.py: the Edge endpoint returned nothing for {voice} (not one of its voices? `edge-tts -l`)')
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lesson', type=int, action='append', help='only these lessons (repeatable)')
    ap.add_argument('--force', action='store_true', help='make again even when unchanged')
    ap.add_argument('--dry-run', action='store_true', help='print what would be sent, call nothing')
    ap.add_argument('--backend', choices=('azure', 'edge'), default='azure')
    ap.add_argument('--rate', default='-10%', help='speaking rate, e.g. -10%% (a little slower for learners); "" for normal')
    ap.add_argument('--female', default=VOICES['female'])
    ap.add_argument('--male', default=VOICES['male'])
    a = ap.parse_args()

    say = azure if a.backend == 'azure' else edge
    voices = {'female': a.female, 'male': a.male}
    who, fixes = tsv('course/voices.tsv'), tsv('course/tts_fix.tsv')
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    made = kept = chars = 0
    for p in sorted((ROOT / 'course/lessons').glob('[0-9][0-9][0-9].yaml')):
        n = int(p.stem)
        if a.lesson and n not in a.lesson:
            continue
        y = yaml.safe_load(p.read_text(encoding='utf8'))
        order = list(dict.fromkeys(d['speaker'] for d in y['dialogue']))
        entry = {}
        for i, d in enumerate(y['dialogue'], 1):
            sex = who.get(d['speaker']) or ('female' if order.index(d['speaker']) == 0 else 'male')
            voice, text = voices[sex], spoken(d['hanzi'], fixes)
            h = hashlib.sha1(f'{voice}|{a.rate}|{text}'.encode('utf8')).hexdigest()[:10]
            f = OUT / f'{n:03d}' / f'{i:02d}.mp3'
            entry[str(i)] = {'h': h, 't': text}
            if not a.force and f.exists() and index.get(str(n), {}).get(str(i), {}).get('h') == h:
                kept += 1; continue
            if a.dry_run:
                print(f'{n:03d}/{i:02d}  {voice:24}  {text}'); continue
            data = say(text, voice, a.rate)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            made += 1; chars += len(text)
            print(f'{n:03d}/{i:02d}  {text}')
        # drop files of lines that no longer exist
        for old in (OUT / f'{n:03d}').glob('*.mp3') if (OUT / f'{n:03d}').exists() else []:
            if str(int(old.stem)) not in entry and not a.dry_run:
                old.unlink()
        if not a.dry_run:
            index[str(n)] = entry
    if not a.dry_run:
        OUT.mkdir(exist_ok=True)
        INDEX.write_text(json.dumps(dict(sorted(index.items(), key=lambda kv: int(kv[0]))), indent=1) + '\n')
    print(f'{made} made ({chars} characters), {kept} unchanged')


if __name__ == '__main__':
    main()
