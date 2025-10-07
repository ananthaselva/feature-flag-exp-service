#useful commands

#activate env
/.venv/Scripts/Activate.ps1

#seed data
python .\scripts\seed.py

#install and use isort
pip install isort
python -m isort app/ scripts/ tests/

#use black

python -m black app/ scripts/ tests/

#pip upgrade 
python -m pip install --upgrade pip

#lint
python -m pylint app/ scripts/  

#mypy
python -m mypy app/ scripts/

#ruff-check
 ruff format --check app tests

#ruff-format
 ruff format app tests