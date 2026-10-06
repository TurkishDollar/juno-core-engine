# JUNO CORE ENGINE

Testnet-only crypto AI monitoring and paper execution system.

## Safety defaults

- `BINANCE_TESTNET=true` is required.
- `TRADING_ENABLED=false` by default.
- Orders are rejected unless both flags are explicitly enabled.
- No module fabricates data: missing credentials or provider errors produce `UNAVAILABLE`.
- The system never accepts mainnet Binance URLs.

## Local start

```bash
cp .env.example .env
# Fill secrets only when ready
chmod 600 .env
docker compose up --build
```

Dashboard: `http://localhost:8000/`
Health: `http://localhost:8000/health`

This repository is a build artifact for a later persistent deployment. It is not yet 24/7-hosted from the Sandbox.

## Railway deployment preparation

- Railway uses the root `Dockerfile` and `railway.json`.
- The app listens on `0.0.0.0` and reads Railway's injected `$PORT`; locally it falls back to `8000`.
- Do **not** deploy the `db` service from `docker-compose.yml` to Railway. Add Railway's managed PostgreSQL service to the project and provide its generated `DATABASE_URL` as a Railway Variable.
- Railway may provide `DATABASE_URL` as `postgresql://...` or `postgres://...`; the app normalizes either form to `postgresql+asyncpg://...`.
- Copy the keys from `.env.example` into Railway Variables. Never commit `.env` or paste secrets into `railway.json`.
- Set `TRADING_ENABLED=false` initially; enable no order execution until Testnet-only validation and an explicit safety review are complete.
