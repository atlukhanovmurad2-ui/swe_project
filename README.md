```
# AI Food Analyzer
```

```
> Upload a photo of a meal and get the detected ingredients with estimated
> portions, per-ingredient nutrition, total calories, and a macronutrient
> breakdown.
```

```
**Team:** [Team_3_M503] • **Topic:** [2] • **Course:** AI-ENG-110 Software
Engineering, AI Academy
```

```
**Due:** **Sep 19, 2026 at 23:59 (UTC+4)**
---
## Quick start
```bash
# 1. Clone & install
git clone https://github.com/atlukhanovmurad2-ui/swe_project.git
cd swe_project
python -m venv .venv
# Windows PowerShell
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
# 2. Configure
cp .env.example .env
# Then fill in the required API keys.
# DO NOT commit .env — it is in .gitignore.
```

```
# Regenerate sample images if needed
python data/_make_samples.py
```

```
# 3. Run the smoke tests
python -m pytest tests/test_ai_smoke.py
# Run the full test suite
python -m pytest -q
# 4. Run the demo
```

```
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```
```

```
The application can run without API keys or a database by using the offline
providers and the in-memory history log.
```

```
## Run with Docker
### 1. Build the application image
```

```
Run this command from the project root:
```

```
```powershell
```

```
docker build -t foodanalyzer .
```
```

```
### 2. Create the Docker network
```

```
The Docker network allows the Food Analyzer API container to communicate
with the PostgreSQL container.
```

```
```powershell
docker network create foodanalyzer-network
```
```

```
This command only needs to be run once.
```

```
### 3. Start PostgreSQL
```

```
Create and start the PostgreSQL container:
```

```
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
```

```
The named Docker volume `foodanalyzer-db-data` keeps the PostgreSQL data
even when the database container is stopped.
```

```
For Docker-to-Docker communication, set the following value in `.env`:
```

```
```env
DATABASE_URL=postgresql+asyncpg://postgres:dev@foodanalyzer-db:5432/foodanalyzer
```
```

```
Also configure the required LLM and USDA API keys in `.env`.
```

```
If the PostgreSQL container already exists but is stopped, start it with:
```

```
```powershell
docker start foodanalyzer-db
```
```

```
### 4. Run the API container
```

```
```powershell
docker run --rm `
  --name foodanalyzer-api `
  --network foodanalyzer-network `
  -p 8000:8000 `
  --env-file .env `
  foodanalyzer
```
```

```
The API is available at:
```

```
```text
http://localhost:8000
```
```

```
Swagger documentation is available at:
```text
http://localhost:8000/docs
```
```

```
Keep the API container running and open another terminal or PowerShell
window in the project directory to test it.
```

```
On Windows PowerShell:
```

```
```powershell
curl.exe -F "image=@data/rice_chicken_broccoli.png"
http://localhost:8000/analyze
```
```

```
On Linux/macOS:
```

```
```bash
curl -s -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
```
```

```
### 5. Run the CLI in Docker
```

```
The same Docker image can also run the CLI:
```

```
```powershell
docker run --rm `
  --network foodanalyzer-network `
  --env-file .env `
  foodanalyzer `
  python -m foodanalyzer analyze data/broccoli_egg.png
```
```

```
### 6. Run a completely offline Docker demo
```

```
The application can also be demonstrated without API keys or PostgreSQL:
```

```
```powershell
docker run --rm `
  foodanalyzer `
  python -m foodanalyzer analyze data/broccoli_egg.png --offline --no-store
```
```

```
### 7. Stop PostgreSQL
```

```
When finished:
```

```
```powershell
docker stop foodanalyzer-db
```
```

```
The PostgreSQL data remains stored in the `foodanalyzer-db-data` Docker
volume.
```

```
## Environment variables
| Variable | Required? | Default | What it controls |
|---|---|---|---|
| `LLM_PROVIDER` | yes for real AI | `anthropic` | VLM provider |
| `LLM_MODEL` | yes for real AI | `claude-sonnet-4-6` | Model ID |
```

```
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` | one for real AI |
```

```
— | API key matching the selected provider |
```

- `| `NUTRITION_PROVIDER` | yes for real lookup | `usda` | Nutrition provider |` 

- `| `USDA_API_KEY` | yes for USDA | — | USDA FoodData Central API key |` 

- `| `DATABASE_URL` | no | in-memory | PostgreSQL connection |` 

- `| `LOG_LEVEL` | no | `INFO` | Logging level |` 

- `| `NUTRITION_CACHE_TTL_SECONDS` | no | `86400` | Nutrition cache lifetime per ingredient | | `MAX_IMAGE_SIZE_MB` | no | `5` | Maximum image upload size |` 

- `| `MAX_CONCURRENCY` | no | `10` | Semaphore limit for concurrent lookups | | `RETRY_MAX_ATTEMPTS` | no | `4` | Maximum retry attempts |` 

- `| `RETRY_BASE_DELAY_SECONDS` | no | `0.5` | Initial retry delay |` 

- `| `RETRY_MAX_DELAY_SECONDS` | no | `8` | Maximum retry delay |` 

- `| `HTTP_PORT` | no | `8000` | API port |` 

```
The full list is in `.env.example`.
```

```
**Do not commit a real `.env` file.**
```

```
With no API keys and no database, the application can still run end-to-end
using the offline providers and in-memory history log.
```

```
## How to run the demo
### CLI
For an offline run that does not require API keys:
```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```
For real providers using the API keys configured in `.env`:
```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png
```
Analyze another image:
```bash
python -m foodanalyzer analyze /path/to/meal.jpg
```
Produce JSON output:
```bash
python -m foodanalyzer analyze data/salad_chicken.png --offline --json
```
Display recent analysis history:
```bash
python -m foodanalyzer history --limit 10
```
Example CLI output:
```

```
```text
ingredient              g    kcal  protein  carbs  fat
------------------------------------------------------
white rice (cooked)     180  234   4.9      50.4   0.5
grilled chicken breast  150  248   46.5     0.0    5.4
```

```
broccoli                 80   27    2.2      5.6    0.3
------------------------------------------------------
TOTAL                    410  509   53.6     56.0   6.3
macro split (energy): protein 42%  carbs 53%  fat 5%
```
```

```
### HTTP API
Start the API directly:
```bash
python -m foodanalyzer.api
```
It can also be started with Uvicorn:
```bash
uvicorn foodanalyzer.api:app --port 8000
```
```

```
The available endpoints are:
```

```
| Method & path | Description |
|---|---|
| `POST /analyze` | Multipart image upload → analysis JSON |
| `GET /health` | Liveness, storage backend, and record count |
| `GET /history?limit=20` | Recent analyses |
| `GET /history/{id}` | One stored analysis |
```

```
### Test `/analyze` with curl
```

```
Linux/macOS:
```

```
```bash
curl -s -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
```
```

```
If `jq` is installed:
```bash
curl -s -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
| jq
```
```

```
Windows PowerShell:
```

```
```powershell
curl.exe -F "image=@data/rice_chicken_broccoli.png"
http://localhost:8000/analyze
```
```

```
Example response:
```

```
```json
{
  "id": "7b0f…",
  "status": "ok",
  "image_filename": "rice_chicken_broccoli.png",
  "ingredients": [
    {
      "name": "white rice (cooked)",
      "estimated_grams": 180.0,
      "confidence": 0.85,
```

```
      "status": "ok",
      "matched_food": "Rice, white, cooked",
      "nutrition": {
        "kcal": 234.0,
        "protein_g": 4.86,
        "carbs_g": 50.4,
        "fat_g": 0.54
      }
    }
  ],
  "totals": {
    "kcal": 509.0,
    "protein_g": 53.6,
    "carbs_g": 56.0,
    "fat_g": 6.3,
    "protein_pct": 42.0,
    "carbs_pct": 53.0,
    "fat_pct": 5.0
  },
  "warnings": []
}
```
```

```
### API error responses
```

```
Error responses have the following structure:
```

```
```json
{
  "error": {
    "code": "...",
    "message": "..."
  }
}
```
```

```
The API uses matching HTTP status codes:
```

```
- `415` — uploaded file is not a supported image
- `413` — uploaded image is too large
- `422` — required multipart field is missing
- `502` — VLM or USDA provider is unavailable
```

```
An unrecognised meal is not treated as an HTTP error. It returns HTTP `200`
with:
```json
{
  "status": "unknown_meal"
}
```
---
## PostgreSQL history log
For a simple local PostgreSQL setup outside the full Docker network setup:
```bash
docker run -d --name pg -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16
```
```

```
Then set:
```

```
```bash
```

```
export DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
```
```

```
The `analysis_history` table is created automatically on the first
connection.
```

```
It stores information including:
```

- `analysis ID` 

- `timestamp` 

- `image path` 

- `ingredients` 

- `totals` 

- `warnings` 

```
When a valid PostgreSQL connection is not available, the application can
use the in-memory history repository.
```

```
## Sequential vs concurrent benchmark
```

```
Nutrition lookups for multiple ingredients are I/O-bound.
```

```
The concurrent pipeline performs independent nutrition lookups concurrently
using `asyncio.gather` and a semaphore that limits the maximum number of
simultaneous operations.
```

```
| Workload | Sequential | Concurrent (sem=10) | Speedup |
|---|---:|---:|---:|
| Nutrition lookup benchmark | 1.206 s | 0.208 s | 5.8× |
```

```
**Reproduce:**
```

```
```bash
python scripts/benchmark_pipeline.py
```
```

```
Measured results:
```

```
```text
Sequential: 1.206 s
Concurrent: 0.208 s
Speedup: 5.8x
```
```

```
The remaining execution time is affected by provider/network latency and
the configured concurrency limit.
```

```
See the project report for the detailed concurrency discussion.
```

```
## Testing
Run the provided AI smoke tests:
```

```
```bash
python -m pytest tests/test_ai_smoke.py
```
```

```
Run the complete test suite:
```

```
```bash
python -m pytest -q
```
```

```
Run the test suite with coverage:
```

```
```bash
python -m pytest -q --cov=foodanalyzer --cov-report=term-missing
```
```

```
- Total coverage: approximately **87%**
```

- `Provided `tests/test_ai_smoke.py`: **passing**` 

- `Tests run without requiring real external AI calls where providers are mocked or replaced by offline implementations.` 

```
The SE-layer test suite covers:
```

- `configuration` 

- `validation` 

- `retries` 

- `TTL nutrition cache` 

- `concurrent nutrition pipeline` 

- `semaphore bound` 

- `storage` 

- `analyzer branches` 

- `CLI` 

- `API` 

# `## Project layout` 

```
```text
.
├── ai/                              # PROVIDED — do not modify
│
├── foodanalyzer/
│   ├── config.py                    # typed settings
```

- `│   ├── models.py                    # result/data models │   ├── errors.py                    # exception hierarchy │   ├── validation.py                # image validation │   ├── offline.py                   # offline fake providers │   │ │   ├── services/` 

- `│   │   ├── retry.py                 # retry + exponential backoff` 

- `│   │   ├── nutrition_cache.py       # TTL nutrition cache │   │   └── ai_service.py            # AI provider integration │   │` 

- `│   ├── concurrency/` 

```
│   │   └── pipeline.py              # asyncio + semaphore
│   │
│   ├── core/
│   │   └── analyzer.py              # end-to-end analysis pipeline
│   │
│   ├── storage/                     # in-memory + PostgreSQL repositories
│   ├── cli.py                       # CLI
│   └── api.py                       # FastAPI application
│
├── tests/
├── data/                             # sample input images
├── artefacts/                        # sample run outputs
├── scripts/
```

```
│   └── benchmark_pipeline.py
│
```

```
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```
```

```
## Architecture in one diagram
```

```
```text
                    +----------------+
                    |      User      |
                    +-------+--------+
                            |
                   +--------+--------+
                   |                 |
                   v                 v
                  CLI            FastAPI API
                   \                 /
                    \               /
                     v             v
                    Analyzer Pipeline
                           |
             +-------------+-------------+
             |                           |
             v                           v
            VLM                  Nutrition Provider
                                           |
                                       TTL Cache
             |                           |
             +-------------+-------------+
                           |
                           v
                    Compute Totals
                           |
                           v
                      Repository
                           |
                  +--------+--------+
                  |                 |
                  v                 v
             PostgreSQL        In-memory
```
```

```
The CLI and HTTP API use the same analysis pipeline.
The main flow is:
```text
Meal image
    |
    v
Validate image
    |
    v
Identify ingredients using VLM
    |
    v
Look up nutrition concurrently
    |
    v
Use/reuse TTL cache
    |
```

```
    v
Compute totals
    |
    v
Store history
    |
    v
Return result
```
---
```

```
## Sample Run Artefact
```

```
The output of one complete Food Analyzer run is included in:
```

```
```text
artefacts/sample_analysis.json
```
```

```
It can be reproduced with:
```

```
```bash
python -m foodanalyzer analyze data/broccoli_egg.png --json
```
```

# `## Limitations` 

- `Ingredient identification depends on the quality of the meal image and the VLM response.` 

- `Portion sizes are estimates rather than exact measurements.` 

- `Real nutrition lookup depends on USDA FoodData Central availability and successful API responses.` 

- `The application does not provide automatic failover between different AI providers.` 

- `External provider latency can affect analysis time.` 

- `The in-memory repository does not persist history after the process stops.` 

```
See the project report for a full discussion of the limitations.
```

# `## Tools & acknowledgements` 

```
The provided `ai/` package was kept unchanged.
```

```
AI assistants were used during development for code explanation, debugging,
review, and assistance with parts of the implementation. AI assistant usage
is also described in the project report and contribution statement.
```

# `## License` 

```
This project is academic coursework for AI-ENG-110 Software Engineering at
AI Academy.
```

