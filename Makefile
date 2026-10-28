.PHONY: install paper live test docker

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest
	cp -n config.example.yaml config.yaml || true
	cp -n .env.example .env || true

paper:
	set -a; . ./.env; set +a; python -m hexcat

live:
	set -a; . ./.env; set +a; HEXCAT_LIVE=1 python -m hexcat --live

test:
	python -m pytest -q

docker:
	docker build -t hexcat . && docker run --env-file .env -v $$PWD/graveyard.sqlite:/app/graveyard.sqlite hexcat
