# AI Food Analyzer

Upload a photo of a meal → get the ingredients with estimated portions, the
per-ingredient nutrition, total calories and a macronutrient breakdown.

The AI core (`ai/`, provided and unchanged) does three things: identify
ingredients with a VLM, look up nutrition facts from USDA FoodData Central,
and sum totals. This repo is the **software-engineering layer** around it:
config, an HTTP API, a CLI, parallel + cached + retried lookups, a PostgreSQL
history log, validation, logging, tests and a container image.

```
foodanalyzer/
├── config.py              typed settings (pydantic-settings)
├── models.py              AnalysisResult / AnalysisRecord / MacroBreakdown
├── errors.py              exception hierarchy → HTTP status + code
├── validation.py          magic-byte + size + type checks
├── offline.py             keyless fake providers (demo / CLI --offline / tests)
├── services/
│   ├── retry.py           exponential-backoff helper (sync + async)
│   ├── nutrition_cache.py TTL cache + retry wrapper around NutritionProvider
│   └── ai_service.py      retry/logging around ai.identify_ingredients
├── concurrency/pipeline.py  asyncio.gather + Semaphore for parallel lookups
├── core/analyzer.py       the end-to-end pipeline
├── storage/               HistoryRepository: in-memory + PostgreSQL (asyncpg)
├── cli.py                 python -m foodanalyzer
└── api.py                 FastAPI: POST /analyze, GET /history, GET /health
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then edit — every value has a working default
python data/_make_samples.py   # regenerate sample images if needed
```

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` / `LLM_MODEL` | `anthropic` / `claude-sonnet-4-6` | VLM selection |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` | – | one, matching the provider |
| `NUTRITION_PROVIDER` | `usda` | nutrition source |
| `USDA_API_KEY` | – | free: <https://fdc.nal.usda.gov/api-key-signup> |
| `DATABASE_URL` | – (in-memory) | `postgresql://user:pass@host:5432/db` |
| `LOG_LEVEL` | `INFO` | `logging` level |
| `NUTRITION_CACHE_TTL_SECONDS` | `86400` | cache lifetime per ingredient |
| `MAX_IMAGE_SIZE_MB` | `5` | upload size limit |
| `MAX_CONCURRENCY` | `10` | semaphore bound on parallel lookups |
| `RETRY_MAX_ATTEMPTS` / `RETRY_BASE_DELAY_SECONDS` / `RETRY_MAX_DELAY_SECONDS` | `4` / `0.5` / `8` | backoff policy |
| `HTTP_PORT` | `8000` | API port |

With no API keys and no database the app still runs end-to-end via the offline
providers and the in-memory history log.

## CLI

```bash
# Offline (no keys, no network) — great for a first run:
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline

# Real providers (needs LLM + USDA keys in .env):
python -m foodanalyzer analyze /path/to/meal.jpg

python -m foodanalyzer analyze data/salad_chicken.png --offline --json
python -m foodanalyzer history --limit 10
```

```
ingredient              g    kcal  protein  carbs  fat
------------------------------------------------------
white rice (cooked)     180  234   4.9      50.4   0.5
grilled chicken breast  150  248   46.5     0.0    5.4
broccoli                80   27    2.2      5.6    0.3
------------------------------------------------------
TOTAL                   410  509   53.6     56.0   6.3

macro split (energy): protein 42%  carbs 53%  fat 5%
```

## HTTP API

```bash
python -m foodanalyzer.api            # or: uvicorn foodanalyzer.api:app --port 8000
```

| Method & path | Description |
|---|---|
| `POST /analyze` | multipart `image` upload → analysis JSON |
| `GET /health` | liveness + storage backend + record count |
| `GET /history?limit=20` | recent analyses |
| `GET /history/{id}` | one record |

```bash
curl -s -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze | jq
```

In windows powershell
```bash
curl.exe -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
```

```json
{
  "id": "7b0f…",
  "status": "ok",
  "image_filename": "rice_chicken_broccoli.png",
  "ingredients": [
    {"name": "white rice (cooked)", "estimated_grams": 180.0, "confidence": 0.85,
     "status": "ok", "matched_food": "Rice, white, cooked",
     "nutrition": {"kcal": 234.0, "protein_g": 4.86, "carbs_g": 50.4, "fat_g": 0.54}}
  ],
  "totals": {"kcal": 509.0, "protein_g": 53.6, "carbs_g": 56.0, "fat_g": 6.3,
             "protein_pct": 42.0, "carbs_pct": 53.0, "fat_pct": 5.0},
  "warnings": []
}
```

Error responses are `{"error": {"code": "...", "message": "..."}}` with a
matching HTTP status: `415` non-image, `413` too large, `422` missing field,
`502` VLM/USDA unavailable. An unrecognised meal is **not** an error — it
returns `200` with `"status": "unknown_meal"`.

### PostgreSQL history log

```bash
docker run -d --name pg -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16
export DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
```

The `analysis_history` table (id, timestamp, image path, ingredients, totals,
warnings) is created automatically on first connect.

## Sequential vs Concurrent Benchmark

Nutrition lookups for multiple ingredients are I/O-bound. The concurrent
pipeline performs independent lookups concurrently using `asyncio.gather`
with a semaphore limiting the maximum concurrency.

Run the benchmark with:

```bash
python scripts/benchmark_pipeline.py
```
Measure results:
Sequential: 1.206 s
Concurrent: 0.208 s
Speedup: 5.8x

## Tests

```bash
python -m pytest tests/test_ai_smoke.py 
python -m pytest -q                  # offline, no network
python -m pytest -q --cov=foodanalyzer --cov-report=term-missing 
```

The provided `tests/test_ai_smoke.py` is kept intact; the SE-layer suite adds
~70 tests covering config, validation, retries, the TTL cache, the parallel
pipeline (including the semaphore bound), storage, the analyzer branches, the
CLI and the API. Coverage is ~87%. (python -m pytest --cov=foodanalyzer --cov-report=term-missing)

## Docker

### 1. Build the application image

From the project root:

```powershell
docker build -t foodanalyzer .
```

### 2. Create the Docker network

This network allows the API container to communicate with PostgreSQL:

```powershell
docker network create foodanalyzer-network
```

This command only needs to be run once.

### 3. Start PostgreSQL

Create and start the PostgreSQL container:

```powershell
docker run -d `
  --name foodanalyzer-db `
  --network foodanalyzer-network `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=dev `
  -e POSTGRES_DB=foodanalyzer `
  -v foodanalyzer-db-data:/var/lib/postgresql/data `
  -p 5432:5432 `
  postgres:16
```

For Docker-to-Docker communication, set the following in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:dev@foodanalyzer-db:5432/foodanalyzer
```

Also configure the required LLM and USDA API keys in `.env`.

If the database container already exists but is stopped, start it with:

```powershell
docker start foodanalyzer-db
```

### 4. Run the API

```powershell
docker run --rm `
  --name foodanalyzer-api `
  --network foodanalyzer-network `
  -p 8000:8000 `
  --env-file .env `
  foodanalyzer
```

The API is then available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```
To run curl open a new terminal or a powershell in the same direcotry and use:

```powershell
curl.exe -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
```
### 5. Run the CLI in Docker

The same image can also run the CLI:

```powershell
docker run --rm `
  --network foodanalyzer-network `
  --env-file .env `
  foodanalyzer `
  python -m foodanalyzer analyze data/broccoli_egg.png
```

For a completely offline demonstration without API keys or PostgreSQL:

```powershell
docker run --rm `
  foodanalyzer `
  python -m foodanalyzer analyze data/broccoli_egg.png --offline --no-store
```

### Stopping PostgreSQL

```powershell
docker stop foodanalyzer-db
```

The PostgreSQL data is persisted in the `foodanalyzer-db-data` Docker volume.

## Sample Run Artefact

The output of one complete Food Analyzer run is included in:

`artefacts/sample_analysis.json`

It can be reproduced with:

```bash
python -m foodanalyzer analyze data/broccoli_egg.png --json
```