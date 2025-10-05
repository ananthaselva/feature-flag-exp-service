.PHONY: run up down seed lint fmt type test ci

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up --build

down:
	docker compose down -v

seed:
	PYTHONPATH=. python -m scripts.seed

lint:
	ruff check .

fmt:
	black .

type:
	mypy app

test:
	pytest -q

ci: lint type test
