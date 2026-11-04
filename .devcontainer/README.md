# TransitOS dev container

Everything a GitHub Codespace needs: Python 3.11, Node 20, MongoDB 7,
the backend virtualenv, the frontend packages and a dev `.env`.

## Create a Codespace

1. **Code** → **Codespaces** → **Create codespace on main**
2. Wait for the post-create script to finish.
3. Open a terminal in the Codespace.

The ports it exposes:

| Port | What |
|---|---|
| 8000 | the TransitOS API (`uvicorn`) |
| 8081 | the Expo dev server |
| 27017 | MongoDB |

## Already in a Codespace?

Skip this directory entirely — run the standalone bootstrap, which works
whether or not `.devcontainer/` was used to create the Codespace:

```bash
cd /workspaces/TransitOS
bash backend/scripts/setup_codespace.sh
```

`.devcontainer/` only affects Codespaces created **after** it was
committed. For an existing Codespace, use the script above.

## First run

```bash
# 1. API
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000

# 2. demo accounts for every role
cd backend
../.venv/bin/python -m scripts.seed

# 3. app
cd frontend
npx expo start
```

Full walkthrough, including the ten demo logins:
**[`docs/DEMO_ACCOUNTS.md`](../docs/DEMO_ACCOUNTS.md)**.

## What the post-create script does

`.devcontainer/post-create.sh` (also safe to run on a plain machine):

1. creates `.venv` and installs `backend/requirements.txt`
2. writes `backend/.env` from `backend/.env.example` with dev defaults
   (it never overwrites an existing `.env`)
3. creates the MongoDB indexes
4. runs `npm ci` in `frontend/`

MongoDB itself comes from the `mongodb` devcontainer feature and is
started for you.

## Running outside a Codespace

The same script works on any machine with Python 3.11+, Node 20+ and a
MongoDB:

```bash
bash .devcontainer/post-create.sh
sudo service mongodb start      # or: docker run -d -p 27017:27017 mongo:7
```

## Checks

```bash
cd backend && ../.venv/bin/python -m pytest -q                    # 215 tests
cd backend && ../.venv/bin/python ../tools/contract/check.py      # 9 checks
cd frontend && npx tsc --noEmit                                  # 0 errors
cd frontend && npx expo-doctor                                   # 18/18
```
