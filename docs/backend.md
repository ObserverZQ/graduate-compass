# activate and deactive venv for python
source .venv/bin/activate
deactivate

## local dev server
uvicorn apps.api.main:app --reload