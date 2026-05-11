source .venv/bin/activate
deactivate
uvicorn apps.api.main:app --reload