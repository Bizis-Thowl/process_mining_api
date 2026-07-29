# Process Mining API

>:warning: **Note**
>
>For this project to work, you need a running Arize-Pheonix instance, a running qdrant-database and a model providor. Each instance can be theoretically hosted via local docker containers.

To start work with this repository, first create a `.env`-file form the `.env-example`-file.

Create the venv from the `pyproject.toml` via:

```bash
uv venv
uv sync
```

With uvicorn for local testing or gunicorn for production environments, start the application via the commandline in the projectfolder:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Via gunicorn:

```bash
.venv/bin/gunicorn --worker-class asgi --workers 1 app:app
```
