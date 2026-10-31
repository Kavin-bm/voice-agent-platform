# Voice Agent Platform

A self-hosted control plane for running many clients' phone agents on one deployment. An operator creates a tenant, fills in a business, and publishes an agent from a role template. [Dograh](https://github.com/dograh-hq/dograh) places and answers the calls. This repository does not stream audio.

**Who it is for.** An agency or in-house operator who onboards client businesses (a clinic, a salon, a sales desk) onto voice agents and keeps each client's data separate. Callers never use this app. There is no public signup: a platform admin key creates each tenant, and that tenant's users log in with email and password.

**How it is built.** A FastAPI service owns tenants, businesses, agent versions, policies, knowledge, credentials, campaigns, and call records. A Next.js dashboard talks to it with a JWT. Postgres stores the data and pgvector stores document chunks. Redis backs one ARQ worker that parses and embeds uploads. MinIO stores the uploaded files. Publishing an agent compiles a runtime-neutral spec, then one adapter turns that spec into a Dograh workflow over HTTP. Dograh is a separate service. It is vendored at `runtime/dograh` only as a schema reference and is never imported.

## Architecture

```mermaid
flowchart TB
  caller["Caller"] --> tel["Telephony"]

  subgraph dograh["Dograh OSS"]
    tel --> stt["STT"]
    stt --> llm["LLM"]
    llm --> tts["TTS"]
    tts --> caller
    llm --> tools["Workflow tools"]
  end

  subgraph control["Control plane"]
    dash["Dashboard"] -->|"JWT"| api["FastAPI"]
    api --> pg[("Postgres + pgvector")]
    api --> redis[("Redis")]
    worker["ARQ worker"] --> redis
    worker --> pg
    worker --> minio[("MinIO")]
    api --> minio
  end

  subgraph tenant["Per tenant"]
    records["Businesses, agents, policies, calls"]
    creds["Fernet-encrypted credentials"]
    account["One synthetic Dograh user"]
  end

  api --> tenant
  api -->|"POST workflow and tools"| dograh
  tools -->|"POST /internal/tools/search-knowledge"| api
  dograh -->|"POST /internal/webhooks/dograh-call-complete"| api
```

The STT, LLM, and TTS boxes are Dograh's pipeline. This repo publishes the workflow graph and receives HTTP callbacks. It does not configure Dograh's speech or model providers yet. See [Voice latency](#voice-latency).

| Dograh does this | This repo keeps it |
|---|---|
| Run the call: telephony, STT, LLM, TTS, barge-in when `allow_interrupt` is set | Tenants, businesses, versions, policies, JWT auth |
| Register tools and dial outbound campaigns | Knowledge parsing, chunking, embeddings, pgvector search |
| Rewrite a Plivo application's answer URL when a number is bound | Credential storage. Telephony credentials are pushed to Dograh on bind. Speech and LLM keys are stored and not pushed |

A tenant is provisioned in Dograh by signing up `tenant-<slug>@tenants.voiceagentplatform.com` the first time a publish or telephony sync needs it. That password is encrypted at rest. Dograh's hosted service-key API is not used.

## Quickstart

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, Docker, git.

```bash
git clone --recurse-submodules https://github.com/Kavin-bm/voice-agent-platform
cd voice-agent-platform
```

Dograh is optional until you publish a workflow or bind a number. The steps below bring up the API and the dashboard without it.

**1. Postgres, Redis, and MinIO**

```bash
cd deploy
docker compose up -d postgres redis minio
cd ..
```

Postgres listens on `localhost:5432` (`voice` / `voice`, database `control_plane`, pgvector enabled). Redis is `localhost:6379`. MinIO is `localhost:9000` with access key `voiceagent` and secret `voiceagent-secret`, matching `control-plane/.env.example`.

**2. API**

```bash
cd control-plane
uv sync
cp .env.example .env
uv run python - <<'PY'
from pathlib import Path
from cryptography.fernet import Fernet
path = Path(".env")
text = path.read_text()
placeholder = "CREDENTIAL_ENCRYPTION_KEY=change-me"
if placeholder not in text:
    raise SystemExit("Fernet placeholder missing; edit .env yourself")
key = Fernet.generate_key().decode()
path.write_text(text.replace(placeholder, f"CREDENTIAL_ENCRYPTION_KEY={key}", 1))
print("wrote CREDENTIAL_ENCRYPTION_KEY")
PY
uv run alembic upgrade head
uv run python ../scripts/seed_templates.py
uv run uvicorn app.main:app --reload
```

`CREDENTIAL_ENCRYPTION_KEY=change-me` is not a Fernet key. The API still boots with it, and the first credential write or Dograh signup then fails. The snippet above replaces only that line. The other `change-me` values in `.env.example` are enough for a local login. Change them before the port is reachable beyond your machine.

The API listens on http://localhost:8000. http://localhost:8000/health returns `{"status":"ok"}`. Interactive docs are at http://localhost:8000/docs.

Seed loads five role templates (`receptionist`, `sales`, `support`, `booking`, `lead_qualification`) and one vertical pack, `receptionist_dental_india`.

**3. First tenant and the dashboard**

`PLATFORM_ADMIN_API_KEY` in the `.env` you just copied is `change-me`. Use an email Dograh and this API will both accept. `owner@acme.test` is rejected: `.test` is a reserved domain.

```bash
curl -sS -X POST http://localhost:8000/api/v1/tenants \
  -H "X-Admin-Key: change-me" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Dental","slug":"acme-dental","owner_email":"owner@example.com","owner_password":"change-me-now"}'
```

```bash
cd ../dashboard
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 and sign in as `owner@example.com` / `change-me-now`. The dashboard defaults to `http://localhost:8000` when `NEXT_PUBLIC_API_URL` is unset. There is no signup page. Use `localhost` in the browser, not `127.0.0.1`, unless that origin is listed in `DASHBOARD_ORIGINS`. The allow-list is matched exactly.

**4. Document ingestion**

Uploads stay queued until the worker is running, in another terminal, from `control-plane/`:

```bash
uv run arq app.workers.worker.WorkerSettings
```

Embedding uses the tenant's OpenAI credential (`provider_type=llm`, `provider_name=openai`) and the model `text-embedding-3-small` (1536 dimensions). A conversational Gemini key does not satisfy that. Supported uploads are PDF, DOCX, XLSX, and TXT. A URL is fetched and parsed as HTML.

## Configuration

The API reads environment variables through `app/core/config.py` (and `control-plane/.env` when you start it from that directory). Defaults below are the code defaults. `.env.example` overrides a few of them for local use.

| Variable | Default | Role |
|---|---|---|
| `ENV` | `dev` | Label only. Not branched on. |
| `DATABASE_URL` | `postgresql+asyncpg://voice:voice@localhost:5432/control_plane` | Async SQLAlchemy URL. |
| `REDIS_URL` | `redis://localhost:6379/0` | ARQ broker. |
| `JWT_SECRET` | `change-me-in-.env` | HMAC secret for access tokens. `.env.example` uses `change-me`. |
| `JWT_ALGORITHM` | `HS256` | `python-jose` algorithm. |
| `JWT_EXPIRES_MINUTES` | `1440` | Access-token lifetime. |
| `PLATFORM_ADMIN_API_KEY` | `change-me-in-.env` | `X-Admin-Key` for `POST /api/v1/tenants`. `.env.example` uses `change-me`. |
| `CREDENTIAL_ENCRYPTION_KEY` | `change-me-in-.env` | Fernet key. Must be generated. See the quickstart. |
| `DOGRAH_BASE_URL` | `http://localhost:8080` | How this process reaches Dograh. `.env.example` matches that. The host override below uses port `18080`. |
| `DOGRAH_CALLBACK_BASE_URL` | `http://host.docker.internal:8000` | How Dograh's containers call this API. |
| `DOGRAH_WEBHOOK_SECRET` | `change-me-in-.env` | `X-Webhook-Secret` on the call-complete webhook. |
| `INTERNAL_TOOL_SECRET` | `change-me-in-.env` | `X-Tool-Secret` on tool webhooks such as knowledge search. |
| `MINIO_ENDPOINT` | `localhost:9000` | Host:port, no scheme. |
| `MINIO_ACCESS_KEY` | `voiceagent` | MinIO access key. |
| `MINIO_SECRET_KEY` | `voiceagent-secret` | MinIO secret key. |
| `MINIO_SECURE` | `false` | TLS to MinIO. |
| `MINIO_DOCUMENTS_BUCKET` | `documents` | Bucket created on first upload. |
| `MINIO_RECORDINGS_BUCKET` | `recordings` | Present in settings. No code writes it. Call recordings store the URL Dograh sends. |
| `DASHBOARD_ORIGINS` | `http://localhost:3000,http://localhost:3001` | CORS allow-list, comma-separated. `localhost` and `127.0.0.1` are different origins. |

`deploy/.env` is a different file, read by `deploy/docker-compose.yml`. Inside that compose file the API and worker override `DATABASE_URL`, `REDIS_URL`, and `MINIO_ENDPOINT` to the compose service names (`postgres`, `redis`, `minio`). Copy `deploy/.env.example` and put a real Fernet key there too.

The dashboard reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Voice latency

A turn inside Dograh is streaming speech-to-text, a language model, and text-to-speech. None of that streaming is implemented in this repository. What follows is only what this code does, plus the gaps that are still plans.

**Streaming STT to LLM to TTS.** `publish_compiled_spec` creates Dograh tools and posts a workflow. It does not open a media socket or stream tokens. `dograh_client.py` states that organization-level STT, LLM, and TTS configuration is not implemented. The dental vertical's provider names (Sarvam `saaras-v3` / `bulbul-v3`, Gemini Flash, Exotel) and its voice knobs (`persona`, `backchannel`, `interruption_sensitivity`, `emotion`, `languages`) are copied into `compiled_spec` by `build_compiled_spec`. `build_workflow_definition` does not read `voice_config` or `provider_stack`. The first thing the workflow asks Dograh to say is the fixed string `Thanks for calling {business name}, how can I help you today?` with `greeting_type: text`.

**Time to first token.** There is no token clock. `Call.first_response_latency_ms` is a nullable float. The comment on that column names a target of p50 under 800 ms and p95 under 1.5 s. Nothing enforces it, and nothing writes the column. The call-complete webhook records duration, disposition, recording URL, transcript URL, direction, campaign id, and dialed number. It has no latency field. `GET /api/v1/analytics/calls` computes `percentile_cont` over non-null latency values and returns `first_response_latency_sample_size`. Until a writer exists, those percentiles are null and the sample size is 0. Filling the column from a Dograh timestamp is a future plan. The 800 ms / 1.5 s figures are that plan's target, not a measurement.

**Barge-in.** The start-call node and the conversation node are published with `allow_interrupt: true`. The end-call node does not set the flag. `interruption_sensitivity` stays in the compiled spec and is not sent. This process does not detect caller audio or stop playback. Whether the caller can talk over the agent depends on Dograh honoring `allow_interrupt`.

**Delay this API does add.** Mid-call knowledge lookup is a blocking HTTP tool, `POST /internal/tools/search-knowledge`. The handler embeds the query with OpenAI `text-embedding-3-small`, then runs a pgvector cosine search over that business's ready chunks, at most 5. Dograh waits for the HTTP response. On failure, including a missing OpenAI key, the handler still returns HTTP 200 with `results: []` and an `error` string. Chunking (220 words, 40-word overlap) happens in the worker before the call, not on this path.

**Future, not built.** Push `provider_stack` and `voice_config` into Dograh. Record a real first-response time on the webhook. Use `Policy.escalation_target` as a second transfer destination. Today that field is stored and injected only as rule text. `transfer_call` dials `Business.default_transfer_number` and no other number.

## Repository layout

```
voice-agent-platform/
├── control-plane/          # FastAPI app, Alembic migrations, Dockerfile, tests
├── dashboard/              # Next.js operator UI
├── templates/              # Five role templates
│   └── verticals/          # Industry overlays. One dental pack is seeded.
├── scripts/                # seed_templates.py, scaffold_vertical.py
├── deploy/                 # Compose file for Postgres, Redis, MinIO, API, worker
└── runtime/dograh/         # Git submodule. Schema reference only.
```

`agent_compiler.py` is the only place a template, vertical pack, business, policies, tools, and voice overrides are merged. `providers/adapters/dograh.py` and `services/dograh_client.py` are the only modules that speak Dograh's JSON.

## Running the API in Docker

From `deploy/`, after filling `deploy/.env`:

```bash
docker compose up -d --build
```

`control-plane-api` runs `alembic upgrade head` and then uvicorn on port 8000. `control-plane-worker` runs the ARQ worker. Dograh is not in this compose file.

## Running Dograh locally

`runtime/dograh` has its own compose file and its own Postgres, Redis, and MinIO. Those published ports collide with `deploy/docker-compose.yml`. A local, uncommitted override drops the internal ports and moves the ones this control plane must reach:

```yaml
# runtime/dograh/docker-compose.override.yml
services:
  postgres:
    ports: !override []
  redis:
    ports: !override []
  minio:
    ports: !override
      - "127.0.0.1:19000:9000"
      - "127.0.0.1:19001:9001"
  api:
    ports: !override
      - "18080:8000"
```

Compose appends list fields unless you use `!override`. MinIO stays published because Dograh hands out presigned URLs.

```bash
cd runtime/dograh && docker compose up -d
```

Point the control plane at it:

```bash
# control-plane process on the host
DOGRAH_BASE_URL=http://localhost:18080
# control-plane process inside deploy/docker-compose.yml
# DOGRAH_BASE_URL=http://host.docker.internal:18080

# Dograh's containers calling back, either way
DOGRAH_CALLBACK_BASE_URL=http://host.docker.internal:8000
```

`DOGRAH_BASE_URL` is how we reach Dograh. `DOGRAH_CALLBACK_BASE_URL` is how Dograh's containers reach us.

## Composing an agent

Compile does not need Dograh. Publish does.

`POST /api/v1/onboard` (JWT, not the admin key) creates the business, agent, draft version, policies, and URL documents, then compiles. With `"publish": true` it also creates the Dograh workflow. A `phone_number` object is bound only when `publish` is true, and only if that tenant already has a telephony credential whose `provider_name` matches `phone_number.provider`.

The same steps exist on their own:

```
POST /api/v1/businesses
POST /api/v1/agents
POST /api/v1/agents/{id}/versions
POST /api/v1/agents/{id}/versions/{v}/policies
POST /api/v1/knowledge-sources
POST /api/v1/knowledge-sources/{id}/documents/upload
POST /api/v1/agents/{id}/versions/{v}/compile
POST /api/v1/agents/{id}/versions/{v}/publish
POST /api/v1/phone-numbers
POST /api/v1/phone-numbers/{id}/bind
```

Publishing creates a new Dograh workflow. It does not delete the previous one. Rollback is binding the number to an older published version.

Built-in tool names are `search_knowledge`, `transfer_call`, `end_call`, `book_appointment`, and `create_lead`. Publish creates Dograh tools for search, end, and transfer (transfer only when the business has `default_transfer_number`). `book_appointment` and `create_lead` are skipped until their tool `config` includes a `url`. A webhook tool with a `url` is posted as Dograh's `http_api` type.

Policies are concatenated into the workflow's global prompt. They are not retrieved from pgvector. `{{business_name}}` in prompts and rules is replaced at compile time.

A new vertical starts as a YAML draft. It is not seeded and not published:

```bash
cd control-plane
uv run python ../scripts/scaffold_vertical.py \
  --template receptionist --name salon \
  --brief "Hair salon: cuts, color, walk-ins versus appointments"
```

That command needs an LLM key on the environment for LiteLLM (`GEMINI_API_KEY` or `OPENAI_API_KEY`, matching `--model`). Review the file under `templates/verticals/`, then rerun `uv run python ../scripts/seed_templates.py`.

## API

Routes under `/api/v1` use a bearer token from `POST /api/v1/auth/login`, except tenant creation, which uses `X-Admin-Key`. `/internal/*` is for Dograh, not the dashboard.

| Prefix | What it does |
|---|---|
| `/auth` | Login. Returns a JWT. |
| `/tenants` | Create and fetch a tenant. Admin key. |
| `/credentials` | Create, list, delete encrypted provider credentials. |
| `/businesses` | Create, list, fetch businesses. |
| `/templates` | List seeded templates and the vertical packs for one template. |
| `/agents` | Agents, versions, compile, publish. |
| `/agents/{id}/versions/{v}/policies` | Create, list, delete policies on a version. |
| `/knowledge-sources`, `/documents` | Sources, upload, URL import, document status. |
| `/phone-numbers` | Register a number and bind it to a published version. |
| `/calls` | List calls and fetch one call with transcript and recording. |
| `/campaigns` | Create, launch, pause, resume, progress. Launch is safe to retry: if Dograh already has a campaign id, a second launch only starts it. |
| `/onboard` | The composite flow above. |
| `/analytics/calls` | Counts by direction, status, and outcome, plus duration and latency percentiles. |
| `/internal/tools/search-knowledge` | Dograh tool. Header `X-Tool-Secret`. |
| `/internal/webhooks/dograh-call-complete` | Dograh webhook. Header `X-Webhook-Secret`. |
| `/health` | Liveness. No auth. |

## Tests

From `control-plane/`:

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
```

The tests cover compilation, the Dograh workflow and tool translation, campaign CSV shape, chunking, Fernet, JWT, the admin key, `/health`, and the quickstart email. They do not need Postgres. GitHub Actions runs the same ruff and pytest commands on pull requests and on pushes to `master`.

Ruff is limited to pyflakes and basic pycodestyle errors (`E4`, `E7`, `E9`, `F`) so generated Alembic revisions are not rewritten for style.

## Not built yet

These are tracked in the code as gaps, not as behavior you can call.

- A real inbound call. Binding code pushes a telephony credential and sets `inbound_workflow_id`. Placing that call still needs a carrier number.
- Applying stored STT, TTS, and conversational LLM credentials to Dograh.
- A draft test-call that does not publish. Dograh has a trigger path, and this client does not use it.
- Writing `Call.first_response_latency_ms`.
- Writing `UsageEvent`. The table exists. No code inserts a row.
- `AgentVersion.model_config` is a JSON column. Compile does not read it.
