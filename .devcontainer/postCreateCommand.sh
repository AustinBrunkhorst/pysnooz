PIP_USER=false poetry install
pre-commit install
PIP_USER=false pre-commit install-hooks
