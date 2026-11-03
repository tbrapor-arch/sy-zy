# make db      sources + course -> data/build/ and app/build/data.js
# make app     app/src + style + data -> app/dist/index.html
# make site    app/dist -> _site/ (what GitHub Pages publishes)
# make lint    check the lessons
PY = python3 -I

.PHONY: all db app site lint test
all: db app

db:
	$(PY) tools/build_db.py

app:
	$(PY) tools/build_app.py

site: all
	$(PY) tools/site.py

lint:
	$(PY) tools/lint.py

test:
	$(PY) tools/romanize.py --test
