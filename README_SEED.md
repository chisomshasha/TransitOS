# Quick reference — seeding accounts

## 1. Add a one-time admin token in Railway

Railway dashboard → your backend service → **Variables** → add:

```
ADMIN_BOOTSTRAP_TOKEN = <openssl rand -hex 32>
```

## 2. Hit the seed endpoint

```bash
curl -X POST https://transitos-production-4b46.up.railway.app/admin/seed \
     -H "X-Admin-Token: <the secret you just set>"
```

## 3. Log in with the returned credentials

| Role | Email | Password (change immediately!) |
|---|---|---|
| Super Admin | `admin@transitos.app` | `Admin#Transit2026!` |
| **Owner** | `owner@transitos.app` | `Owner#Transit2026!` |
| General Manager | `gm@transitos.app` | `Gm#Transit2026!` |

## 4. **DELETE the ADMIN_BOOTSTRAP_TOKEN variable in Railway**

The endpoint is now permanently disabled.

