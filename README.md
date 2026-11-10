# 书橱 Sy-zy · Shanghainese

Open it: https://tbrapor-arch.github.io/sy-zy/ (repository renamed from `syzy` on 3 Nov 2026: Chrome on Android kept a broken install record for the old address) (GitHub Pages, from the root of `main`).

A Shanghainese course in the Assimil style, the sibling of 冊櫥 Tsheh-tû (Taigi) and Mainichi (Japanese): short dialogues, numbered notes, new words, practice, and a review deck. One page, no server; progress stays in the browser.

Shanghainese has no official spelling, and every book uses its own. So the app stores each word **once, in IPA**, and generates the spellings from it: **Wugniu** (the online standard, Wiktionary), **Qian Nairong's pinyin** (his dictionaries and textbooks) and **IPA** with the tune each syllable has inside its word. One correction fixes all three.

## What's in the repo

```
app/src/              the app's code: app.js (lessons, Practice, lists, cards, settings), sync.js (gist sync),
                      module.js (the optional private module: Books tab, Book course)
app/style/            the style (base from Tsheh-tû, recoloured, + extra.css)
app/pwa/              manifest, icons, offline service worker
course/lessons/       001.yaml … the lessons (format: course/README.md); 000-reading.html is lesson 0
course/core.tsv       ~230 core words written by hand: type, English, Mandarin, corrected IPA
course/overrides.tsv  corrections confirmed against a book (win over everything else)
course/verified.tsv   readings confirmed by a book (created by tools/import_notes.py)
data/raw/             the open data the database is built from
data/build/           generated: lexicon.jsonl (~96,000 words, every spelling and tune), report.md
tools/romanize.py     the spelling systems and the tone sandhi: the only place they are defined
tools/build_db.py     sources + course → data/build/ and app/build/data.js
tools/build_app.py    app/src + style + data → app/dist/index.html
tools/site.py         app/dist → _site/ (published by .github/workflows/pages.yml)
tools/lint.py         checks the lessons and the L1–50 curve (docs/course-plan.md)
tools/smoke.py        opens the built app headless and visits every page
course/trad.tsv       fixes to the simplified → traditional conversion (Settings › Characters)
tools/import_notes.py the app's "book notes" file → course/verified.tsv and course/book_notes.tsv
tools/tts.py          synthetic dialogue audio (Azure, wuu-CN voices) → audio/ (run by .github/workflows/audio.yml)
course/voices.tsv     which voice each speaker gets; course/tts_fix.tsv: respellings for the voice
```

## Build

```
pip install -r requirements.txt
make            # database + app → app/dist/index.html
make lint test  # lessons and spellings
make site       # the installable site in _site/
```
GitHub Pages builds and publishes on every push to `main` (Settings › Pages › Source: GitHub Actions).

## The app

Tabs as in Tsheh-tû: **Lessons · Practice · Settings**, plus **Books** (only on a device whose GitHub token can read
the private repository; Settings › Sync and your books). Practice holds
Cards (Leitner review), My lists (words added from any card go to the list of the page you are on), Vocabulary
(search in characters, any spelling, pinyin or English) and Drills. Characters: simplified by default, traditional
in Settings. Progress and lists sync through a secret gist.

## Checking against your books ("training" the database)

The word cards no longer carry a "Your book" section (removed 4 Nov 2026; notes saved earlier stay in the browser
and in sync, unused). Readings are now checked against the books typed in the private repository: matches go to
`course/verified.tsv` ("✓ Checked in …" on the card), accepted differences to `course/overrides.tsv` (word, IPA,
book, note), then rebuild. `tools/import_notes.py` still reads an old book-notes file if one exists.

## Readings: where they come from, how far to trust them

| Source | Used for | Trust |
|---|---|---|
| `data/raw/zaonhe.txt` (chinese-dialect-lexicons, compiled from wugniu.com, MCPDict, rime-yahwe_zaonhe) | the IPA of ~96,000 words | Good for single characters, noisy for words: some carry book or Mandarin-influenced readings (e.g. 闲话 as ɦi ɦuᴀ). |
| `course/core.tsv` | ~230 core words: corrected IPA, English, Mandarin | Written by hand (Claude) from standard references; readings that differ from the lexicon are flagged on the word card. |
| `course/verified.tsv` | readings confirmed by a source | The words of lessons 1–7 were checked on 3 Nov 2026 against wugniu.com (single characters) and Wiktionary (whole words): 133 confirmed, 5 corrected (阿姨, 粢饭团, 阿姐, 请问, 白相). |
| `course/overrides.tsv` | your book corrections | Highest. |

The app follows **new urban Shanghainese** (five tones: 53, 34, 13, 55ʔ, 12ʔ). Word tunes use the left-dominant sandhi patterns (the first syllable sets the melody). That is right for compound words and noun phrases; verb + object phrases can follow other patterns.

Qian's pinyin is generated with his "new speakers" rules (əʔ and ᴀʔ both written -ak), and was tested against the examples he published with his input software (whangpugang, makshy, bhakxiang, cakyhangxiang, linfhakqin, dhaojiangwhu, ghakbhangyhou, shanghehhehho) and against the spelling rules of his 2011 word handbook: ny only before yu (人 nin, 女 nyu), no y after j q x (区 qu, 血 xuik), iu and un after an initial (救 jiu, 困 kun), hh before a voiced syllabic nasal (五 hhng).

## Lesson audio (synthetic)

Every dialogue line can have a ▶ button and the lesson a "Listen to the dialogue" button. The audio is made by
`tools/tts.py` with Microsoft's two Wu Chinese neural voices, `wuu-CN-XiaotongNeural` (female) and
`wuu-CN-YunzheNeural` (male), and published from `audio/` with the site (cached for offline use).

- These voices are only on the **Azure Speech API**. The free Edge "Read aloud" endpoint (speech.platform.bing.com)
  does not have them: it answers with no audio for any `wuu-CN` voice (tested 6 Nov 2026).
- Setup: create a Speech resource in the Azure portal (free tier F0: 500,000 characters a month; the whole course is a
  few thousand), then add the repository secrets `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`. The **Lesson audio**
  workflow then makes the audio for new or changed lines whenever a lesson changes, commits it and rebuilds the site.
  Locally: `AZURE_SPEECH_KEY=… AZURE_SPEECH_REGION=… python3 tools/tts.py` (`--dry-run` shows what would be sent).
- `course/voices.tsv` says who speaks with which voice; `course/tts_fix.tsv` respells words the voice reads wrongly.
- The voice reads characters with its own readings and does not see the lesson's IPA or sandhi: it is a guide to rhythm
  and melody, labelled as synthetic in the app, not a reference for a reading. A line edited after its audio was made
  goes silent until the audio is made again.

## Licences of the data

- CC-CEDICT (`data/raw/cedict_ts.u8`): CC BY-SA 4.0. English glosses and pinyin.
- rime-yahwe_zaonhe (`data/raw/yahwe_zaonhe.dict.yaml`): CC0.
- MCPDict: MIT.
- chinese-dialect-lexicons (`data/raw/zaonhe.txt`): no licence file in the repository; it is built from the sources above and wugniu.com. Ask the author before publishing the app widely.
- jieba (`data/raw/jieba_dict.txt`): MIT. Word frequencies only.

## Sync and your books

Settings › *Sync and your books* takes one fine-grained GitHub token (Repository access: only `syzy-private`,
Contents: Read-only; Account permissions: Gists: Read and write). Progress, lists and book notes are kept in a secret
gist `syzy-progress.json` and merged on every device, as in Tsheh-tû. The same token opens the optional private
module: your own books (Books tab) and the book course. Nothing of them is in this repository or the published page.

## Next

- Lessons 8 onwards (format: `course/README.md`; length: `docs/course-plan.md`).
- Audio from IPA: the open CjangCjengh/Shanghainese-TTS model (Hugging Face) takes IPA, so it could follow the lesson's own readings and sandhi, which the Azure voices cannot.
- A second wave (active phase, English → Shanghainese) from lesson 50, as in Tsheh-tû.
