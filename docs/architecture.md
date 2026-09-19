# Architecture

## Overview

The Food Analyzer application analyzes a meal image and returns the detected ingredients together with their estimated nutritional values.

The application can be used through two interfaces:

* CLI (`foodanalyzer/cli.py`)
* FastAPI API (`foodanalyzer/api.py`)

Both interfaces use the same analysis pipeline.

## Analysis Flow

The main analysis flow is:

```text
Meal Image
    |
    v
Validate Image
    |
    v
Identify Ingredients (VLM)
    |
    v
Look Up Nutrition Data
    |
    v
Compute Nutrition Totals
    |
    v
Store Analysis History
    |
    v
Return Result
```

The main pipeline is implemented in `foodanalyzer/core/analyzer.py`.

## Main Components

### CLI

The CLI allows the user to analyze an image from the terminal.

Example:

```bash
python -m foodanalyzer analyze data/sample_meal.jpg
```

It displays the detected ingredients, estimated grams, calories, protein, carbohydrates, fat, and the total values.

### API

The FastAPI application provides the same functionality through HTTP.

The main endpoint is:

```text
POST /analyze
```

The uploaded image is validated and temporarily saved before being passed to the analysis pipeline.

### Ingredient Identification

A Vision Language Model (VLM) analyzes the meal image and returns detected ingredients with estimated weights.

The application supports online AI providers and offline providers used for testing.

### Nutrition Lookup

After ingredients are detected, the application looks up nutritional information for each ingredient.

Nutrition lookups are performed concurrently so that several ingredients can be processed without waiting for each lookup to finish one by one.

### Cache

Nutrition results are cached using a TTL cache. The default TTL is 24 hours.

If nutrition data for an ingredient is already cached and has not expired, the application reuses it instead of making another request.

### Storage

Analysis history is stored through the repository layer.

PostgreSQL is used when a valid database connection is available. An in-memory repository can be used as a fallback when PostgreSQL is unavailable.

### Error Handling and Retry

External AI and nutrition requests can fail because of network or provider errors. The application uses retry logic with exponential backoff for temporary failures.

Validation errors and application errors are converted into structured responses by the API.

## Concurrency

The project uses `asyncio` for asynchronous operations.

Nutrition lookups can run concurrently and are limited by a semaphore to prevent too many requests from running at the same time. Blocking provider calls can be moved to worker threads so that they do not block the asynchronous event loop.

## High-Level Architecture

```text
             +----------------+
             |      User      |
             +-------+--------+
                     |
              +------+------+
              |             |
             v             v
          CLI          FastAPI API
              \             /
               \           /
                v         v
              Analyzer Pipeline
                     |
          +----------+----------+
          |                     |
          v                     v
         VLM            Nutrition Provider
                                 |
                              TTL Cache
          |                     |
          +----------+----------+
                     |
                     v
              Compute Totals
                     |
                     v
                Repository
                     |
                     v
                 PostgreSQL
```
