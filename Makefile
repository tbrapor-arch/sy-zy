# make db      sources + course -> data/build/ and app/build/data.js
# make app     app/src + style + data -> app/dist/index.html (fetches the fonts once, see data/fetch_fonts.sh)
# make site    app/dist -> _site/ (what GitHub Pages publishes)
# make lint    check the lessons
# make vocab   the common-vocabulary list -> data/build/core_vocab.tsv
# make coverage  what the lessons cover, what to teach next (PRIVATE=../syzy-private adds the books' ranking)
# make plan    check the words planned for lessons 50–100 -> data/build/plan_check.tsv (after make db)
# make packet N=50  everything needed to write lesson 50 -> data/build/packets/050.md (PRIVATE=../syzy-private adds the books)
# make smoke   open the built app headless, visit every page (needs playwright + Chrome)
PY = python3 -I

.PHONY: all db app site lint test smoke vocab coverage plan packet
all: db app

db:
	$(PY) tools/build_db.py

app:
	sh data/fetch_fonts.sh
	$(PY) tools/build_app.py

site: all
	$(PY) tools/site.py

lint:
	$(PY) tools/lint.py

test:
	$(PY) tools/romanize.py --test

smoke:
	python3 tools/smoke.py

vocab:
	$(PY) tools/core_vocab.py

coverage: vocab
	$(PY) tools/coverage.py $(TOP) $(if $(PRIVATE),--private $(PRIVATE))

plan:
	$(PY) tools/plan_check.py

packet:
	$(PY) tools/packet.py $(N) $(if $(PRIVATE),--private $(PRIVATE))
