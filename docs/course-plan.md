# Course plan

Decided 3 Nov 2026 (full working plan, in French, in the claude.ai project: `plan-etape-1.md`).

## Decisions
1. **Progression L1–50 by number of lines** (§3): 6 → 15 lines, +1 every 5 lessons; line length 7 → 11 syllables;
   12 → 20 new words; review lessons 2 lines shorter, no new words.
2. **Default romanization: Wugniu**; Qian Nairong pinyin and IPA in Settings. Script switch as in Tsheh-tû.
3. **Characters: simplified by default**, traditional as an option (home-made table for dialect characters).
4. **Variety: new urban Shanghainese, 5 tones** (53, 34, 13, 55ʔ, 12ʔ).
5. **Repos: `syzy` (public, this one, on Tsheh-tû's layout) + `syzy-private`** (books, book course, media, module).
6. **No Exam tab.** The private module keeps Tsheh-tû's loading contract and carries Books, Book course, podcast,
   video, music.

## 3. Progression L1–50
- Lines: 6 at L1–5, then +1 every 5 lessons → 15 at L46–50.
- Median syllables per line: 7 (L1–10), 8, 9, 10, 11 (L41–50); a single line may be short.
- New words: 12 → 20, linear (±2). Reviews (7, 14 … 49): 2 lines fewer than their neighbours, no new words.
- Exercises: 5 translate + 3 fill, outside the dialogue, already-seen words only.
- `make lint` reports the differences; `python3 tools/lint.py --strict` makes them errors once a lesson is final.

| L | lines | syll./line | new words |
|---|---|---|---|
| 1–5 | 6 | 7 | 12–13 |
| 6, 8–10 | 7 | 7 | 13 |
| 7 R | 5 | 7 | 0 |
| 11–13, 15 | 8 | 8 | 14 |
| 14 R | 6 | 8 | 0 |
| 16–20 | 9 | 8 | 14–15 |
| 21 R | 7 | 9 | 0 |
| 22–25 | 10 | 9 | 15–16 |
| 26, 27, 29, 30 | 11 | 9 | 16–17 |
| 28 R | 9 | 9 | 0 |
| 31–34 | 12 | 10 | 17 |
| 35 R | 10 | 10 | 0 |
| 36–40 | 13 | 10 | 18 |
| 41, 43–45 | 14 | 11 | 19 |
| 42 R | 12 | 11 | 0 |
| 46–48, 50 | 15 | 11 | 19–20 |
| 49 R | 13 | 11 | 0 |

## Steps
1. Structure port. **Done:** layout (`app/ course/ tools/ data/ docs/`), YAML lessons, Makefile, lint with the curve,
   spelling regression test, Pages workflow. **Next:** Tsheh-tû's app template (tabs, lesson page, word card,
   gist sync, private-module loader, CSP) with the Shanghainese layer; `syzy-private` skeleton.
2. `romanize.py`: verb–object sandhi, more tests, simplified → traditional table for dialect characters.
3. `syllabus.yaml` (100 titles + grammar); revise L1–7 to the curve.
4. Write lessons in batches of 7.
5. Phrasebook → `syzy-private/books/`.
6. Book course tab (private): audio + timed lines.
