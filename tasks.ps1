param(
    [string]$task
)

# Activate virtual environment
function Activate-Venv {
    if (-Not (Test-Path ".\.venv")) {
        python -m venv .venv
    }
    . .\.venv\Scripts\Activate.ps1
}

switch ($task) {

    "run" {
        Write-Host "Starting FastAPI app..."
        Activate-Venv
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
    }

    "seed" {
        Write-Host "Seeding database..."
        Activate-Venv
        python scripts/seed_db.py
    }

    "test" {
        Write-Host "Running tests..."
        Activate-Venv
        pytest tests -v --disable-warnings --cov=app --cov-report=term
    }

    "ci" {
        Write-Host "Running CI tasks..."
        Activate-Venv
        ruff check app tests --exit-zero
        mypy app
        pytest tests -v --disable-warnings --cov=app --cov-report=xml
    }

    default {
        Write-Host "Unknown task: $task"
        Write-Host "Available tasks: run, seed, test, ci"
    }
}