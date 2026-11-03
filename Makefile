# make db      sources + course -> data/build/ and app/build/data.js
# make app     app/src + style + data -> app/dist/index.html (fetches the fonts once, see data/fetch_fonts.sh)
# make site    app/dist -> _site/ (what GitHub Pages publishes)
# make lint    check the lessons
# make smoke   open the built app headless, visit every page (needs playwright + Chrome)
PY = python3 -I

.PHONY: all db app site lint test smoke
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
