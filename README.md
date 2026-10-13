# 书橱 Sy-zy · Shanghainese

Open it: https://tbrapor-arch.github.io/syzy/ (GitHub Pages, from the root of `main`).

A Shanghainese course in the Assimil style, the sibling of 冊櫥 Tsheh-tû (Taigi) and Mainichi (Japanese): short dialogues, numbered notes, new words, practice, and a review deck. One page, no server; progress stays in the browser.

Shanghainese has no official spelling, and every book uses its own. So the app stores each word **once, in IPA**, and generates the spellings from it: **Wugniu** (the online standard, Wiktionary), **Qian Nairong's pinyin** (his dictionaries and textbooks) and **IPA** with the tune each syllable has inside its word. One correction fixes all three.

## What's in the repo

```
app/index.html        the app: one self-contained page (open it, or publish it)
app/app.js            the app's code
app/data.js           generated: lessons, the 6,000-word dictionary the app uses, lesson 0, the bridge
lessons/01.txt …      the lessons, in a plain text format (see the top of 01.txt)
lessons/lesson0.html  lesson 0: how to read the spellings
data/core.tsv         ~230 core words written by hand: type, English, Mandarin, corrected IPA
data/overrides.tsv    corrections confirmed against a book (win over everything else)
data/verified.tsv     readings confirmed by a book (created by import_notes.py)
db/lexicon.jsonl      generated: the full database, ~96,000 words, every spelling and tune
db/report.md          generated: what the build had to guess
build/romanize.py     the spelling systems and the tone sandhi: the only place they are defined
build/build_db.py     sources + core + overrides + lessons → db/ and app/data.js
build/build_app.py    app.js + data.js + style → app/index.html
build/import_notes.py the app's "book notes" file → data/verified.tsv and data/book_notes.tsv
sources/              the open data the database is built from
```

## Rebuild

```
pip install opencc-python-reimplemented
python3 build/build_db.py && python3 build/build_app.py
```

## Checking against your books ("training" the database)

1. In the app, open a word and tap **Matches my book** or **My book says…** (write the book's spelling and title).
2. Settings → **Save book notes file**.
3. `python3 build/import_notes.py syzy-book-notes-….json`
   Matches go to `data/verified.tsv` and show as "✓ Checked in …" on the word card.
   Differences go to `data/book_notes.tsv`, with a proposed IPA when the book's spelling can be read back as Wugniu or Qian.
4. Copy the lines you accept into `data/overrides.tsv` (word, IPA, book, note) and rebuild.

## Readings: where they come from, how far to trust them

| Source | Used for | Trust |
|---|---|---|
| `sources/zaonhe.txt` (chinese-dialect-lexicons, compiled from wugniu.com, MCPDict, rime-yahwe_zaonhe) | the IPA of ~96,000 words | Good for single characters, noisy for words: some carry book or Mandarin-influenced readings (e.g. 闲话 as ɦi ɦuᴀ). |
| `data/core.tsv` | ~230 core words: corrected IPA, English, Mandarin | Written by hand (Claude) from standard references; 28 readings differ from the lexicon and are flagged on the word card. Check them first. |
| `data/overrides.tsv` | your book corrections | Highest. |

The app follows **new urban Shanghainese** (five tones: 53, 34, 13, 55ʔ, 12ʔ). Word tunes use the left-dominant sandhi patterns (the first syllable sets the melody). That is right for compound words and noun phrases; verb + object phrases can follow other patterns.

Qian's pinyin is generated with his "new speakers" rules (əʔ and ᴀʔ both written -ak), and was tested against the examples he published with his input software (whangpugang, makshy, bhakxiang, cakyhangxiang, linfhakqin, dhaojiangwhu, ghakbhangyhou, shanghehhehho).

## Licences of the data

- CC-CEDICT (`sources/cedict_ts.u8`): CC BY-SA 4.0. English glosses and pinyin.
- rime-yahwe_zaonhe (`sources/yahwe_zaonhe.dict.yaml`): CC0.
- MCPDict: MIT.
- chinese-dialect-lexicons (`sources/zaonhe.txt`): no licence file in the repository; it is built from the sources above and wugniu.com. Ask the author before publishing the app widely.
- jieba (`sources/jieba_dict.txt`): MIT. Word frequencies only.

## Reader: 《弄堂》 (胡宝谈, 2011)

The Read tab opens the first novel written in Shanghainese, chapter by chapter. The app contains **no text of the novel**: the reader loads their own .epub once, and it stays in their browser. Each prepared chapter ships a pack with the word boundaries, the author's bracketed readings and an English translation, matched to the reader's text by a fingerprint per paragraph.

To prepare a chapter: put your copy at `reader/longtang/book.epub`, add the chapter's words to `reader/longtang/glossary.tsv` (lines starting with `!` stop the splitter from gluing words together), write `reader/longtang/chNN.txt` (one English line per paragraph), rebuild. The book is under copyright: the epub, the translations and `packs.json` are in `.gitignore`. Keep them in a private repo, or out of git.

## Google Drive

On the hosted site the Read page signs in to Google and uses the Drive's hidden app folder, with the same Google client as 书架 Shūjià (same site, tbrapor-arch.github.io). The two apps share that folder: a 弄堂 epub imported in Shūjià is found here. Sy-zy keeps there `syzy-state.json` (lessons done, review deck, book notes, chapters read), `syzy-longtang.epub` (if you loaded the book here) and `syzy-longtang-pack.json` (the study pack).

In the claude.ai version, the page cannot sign in to Google itself: it uses your Google Drive connector, finds a 弄堂 .epub in your Drive and can save your copy there.

## Public and private builds

`app/index.html` and the root `index.html` are public: they hold no text derived from the novel. The build also writes, ignored by git, `app/data.private.js` and `app/artifact.html` (with the English translations, for the private claude.ai version) and `reader/longtang/syzy-longtang-pack.json`, the study pack to load once in the hosted app.

## Next

- Lessons 8 onwards (the format is in `lessons/01.txt`).
- Audio: an open Shanghainese text-to-speech model exists (CjangCjengh/Shanghainese-TTS on Hugging Face, trained on this same data); it takes IPA, so it could voice every word and line.
- A second wave (active phase, English → Shanghainese) from lesson 50, as in Tsheh-tû.
