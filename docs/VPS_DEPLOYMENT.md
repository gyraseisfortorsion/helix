# Vercel frontend + Docker backend

The backend is already FastAPI. This setup runs it on your VPS with its existing worker and SQLite/Parquet storage. The frontend stays at **https://helix-lime-nine.vercel.app**.

## Current deployment

The deployed API is `http://34.31.166.71`. The frontend's `web/vercel.json` forwards `/api/*` to that server through a Vercel external rewrite. Keep `VITE_API_BASE_URL` empty or unset for this mode. Browsers make HTTPS requests to the frontend's own `/api` paths, so the HTTP-only origin does not cause browser mixed-content errors. API responses are explicitly uncached.

The Vercel-to-VPS connection currently uses HTTP. This route supports the demo while the backend has no HTTPS hostname. Use the direct HTTPS setup below for uploads that should avoid the Vercel proxy. To move the proxy to a new backend, update the rewrite destination and redeploy Vercel. To switch to direct API access, configure a trusted HTTPS origin through `VITE_API_BASE_URL` and the matching CORS origins.

## Direct HTTPS deployment

```text
Browser / Vercel frontend
    HTTPS + Authorization + streamed investigation events
VPS / Caddy on ports 80 and 443
    HTTP on the private Docker network
FastAPI container on port 8000, including one job worker
    /data named volume: SQLite, imported files, results and chat history
```

No GPU is required on the VPS when using the hosted AlphaGenome and NVIDIA endpoints. You only need Docker Engine with **Docker Compose v2.24 or newer**, Git, and a hostname pointing to your server.

## First deployment

1. Create a DNS **A record**, for example `api.yourdomain.com`, pointing to the VPS's public IPv4 address. If you also publish an AAAA record, it must reach this VPS over IPv6. Allow inbound TCP ports **80 and 443** in the VPS firewall. Caddy uses these to obtain and renew the HTTPS certificate. UDP 443 is optional for HTTP/3.
2. On the VPS:

   ```bash
   git clone https://github.com/gyraseisfortorsion/helix.git
   cd helix
   cp deploy/vps.env.example .env
   chmod 600 .env
   nano .env
   ```

3. Set these values in `.env`:

   ```dotenv
   API_DOMAIN=api.yourdomain.com
   DNA_CORS_ORIGINS=https://helix-lime-nine.vercel.app,https://helix-gyraseisfortorsions-projects.vercel.app
   ANTHROPIC_API_KEY=your-existing-key
   ALPHAGENOME_API_KEY=your-existing-key
   EVO2_ACCESS_TOKEN=your-existing-NVIDIA-key
   ```

   `API_DOMAIN` is the **backend hostname**, without `https://` or a path. `DNA_CORS_ORIGINS` contains the **frontend origins**, without trailing slashes. The template already sets the hosted Evo 2 endpoint and model name. Empty provider credentials leave the corresponding live features unavailable; they do not prevent the public-data workspace from starting. Provider access still depends on a valid, funded account and permission for the configured model.

4. Start everything:

   ```bash
   docker compose --profile https up -d --build --wait
   curl --fail https://api.yourdomain.com/api/health
   ```

The first build installs the locked Python dependencies. The API health check gates Caddy startup. The containers restart automatically after Docker or the VPS restarts, provided Docker itself starts on boot. Certificate issuance may take a little longer than container startup; inspect `docker compose logs caddy` if the HTTPS check has not succeeded yet.

Public demo users require no account setup. To enable **Use my data**, also set a random `DNA_ACCESS_KEY` in the VPS `.env`, then recreate the API container. Leave it empty for a public demo without private uploads. Loopback workspace bypass is disabled in the container, including behind Caddy.

## Connect the existing Vercel frontend

In the Vercel **helix** project, open **Settings → Environment Variables** and add:

```dotenv
VITE_API_BASE_URL=https://api.yourdomain.com
```

Select **Production**, then **redeploy the frontend**. Vite embeds this public URL during the build. Do not append `/api`: the frontend already supplies that prefix. The backend needs a browser-trusted HTTPS certificate because the Vercel frontend uses HTTPS.

The only value the frontend needs is this API origin. Anthropic, AlphaGenome and NVIDIA keys are read from the VPS container's environment, not from the browser or Vercel. The older encrypted key values in the Vercel project do not configure the VPS backend.

Requests go straight from the browser to the VPS, including uploads and streamed events. They do not pass through Vercel Functions. Only the exact origins in `DNA_CORS_ORIGINS` may make browser API requests. Add another stable frontend domain explicitly if you use one. CORS does not authenticate callers; the existing workspace bearer tokens still scope data access.

## Verify the split deployment

Check the health endpoint, public profiles, DNA data, wearables, optional methylation and CORS from inside the API container:

```bash
docker compose exec -T api python deploy/smoke_test.py \
  https://api.yourdomain.com \
  --origin https://helix-lime-nine.vercel.app
```

To also exercise a queued chat, the worker, saved results and the event stream:

```bash
docker compose exec -T api python deploy/smoke_test.py \
  https://api.yourdomain.com \
  --origin https://helix-lime-nine.vercel.app --chat
```

The chat check uses provider credits if keys are configured. It reports whether the resulting answer is live or evidence-only. Molecular-provider availability flags indicate configuration; they do not prove a key is accepted. In the frontend, also run a specific variant investigation to check the chosen provider.

## Updates, logs and persistence

```bash
git pull --ff-only
docker compose --profile https up -d --build --wait
docker compose ps
docker compose logs --tail 100 api caddy
```

After changing `.env`, run the `up` command again. `docker compose restart` alone does not load new environment values. Use `docker compose --profile https down` to stop the stack. The named volumes remain, so a later `up` restores the same stored workspace data and certificate state. Browser sessions still have their normal eight-hour expiry.

`helix-data` stores the database and all related files. **Do not use `down -v` for a normal stop**, because it deletes these volumes. Back up the complete data volume while the API is stopped so SQLite and the imported files belong to the same snapshot. The template's `COMPOSE_PROJECT_NAME=strand` keeps the production volume names stable even if you rename the checkout directory.

Run exactly **one API container and one Uvicorn process** with the embedded worker. Do not scale replicas or launch another worker against this volume. The current SQLite design is for a single host. Interrupted jobs are reported as retryable after a restart.

## Existing reverse proxy or local Docker check

If your VPS already runs an HTTPS reverse proxy, start only the API:

```bash
docker compose up -d --build --wait api
curl --fail http://127.0.0.1:8000/api/health
```

Configure your existing proxy to forward the backend hostname to `127.0.0.1:8000` and disable buffering for `text/event-stream`. Use a long enough read timeout for molecular requests. Port 8000 is intentionally bound to loopback and is not publicly exposed. Set `API_PORT` if that host port is occupied.

For local Docker checks, a root `.env` is optional. Without keys the workspace starts in evidence-only mode. Use a separate Compose project and data volume when testing so you do not mix test sessions with deployed data.

## Dependency updates

The image installs the hash-checked runtime dependencies exported from the existing `uv.lock`, including the AlphaGenome SDK. After intentionally updating the project lock, regenerate the runtime export before rebuilding:

```bash
uv export --frozen --extra science --no-dev --no-emit-project \
  --format requirements-txt --output-file deploy/requirements.lock
```

Provider keys, local data, frontend dependencies, presentations and `.vercel` files are excluded from the Docker build context. Build and smoke-test the image after updating dependencies.

References: [Caddy automatic HTTPS](https://caddyserver.com/docs/quick-starts/reverse-proxy), [Caddy streaming controls](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming), [Compose readiness checks](https://docs.docker.com/compose/how-tos/startup-order/).
