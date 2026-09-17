# Unreel

Unreel turns Instagram reels and recipe websites into a personal cookbook.

Paste a link, and Unreel extracts a title, ingredients, and steps, then saves the recipe to your account with a thumbnail. Sign in, browse a gallery of what you’ve saved, and open any recipe to cook from it.

## How it works

**Instagram.** Unreel reads the reel caption and thumbnail with [yt-dlp](https://github.com/yt-dlp/yt-dlp). Claude tries to extract a structured recipe from the caption. If ingredients or steps are missing, it downloads the audio, transcribes it with OpenAI, and extracts again.

**Websites.** Unreel fetches the page, prefers JSON-LD `Recipe` data when present, and otherwise uses visible page text. Claude turns that into the same structured format. Thumbnails come from the recipe image or Open Graph image.

Recipes are stored per user in Supabase. Extracting the same source again updates the existing recipe instead of creating a duplicate.

## Stack

| Layer | Tools |
| --- | --- |
| Frontend | React, Vite, React Router |
| Backend | Flask |
| Auth & data | Supabase Auth, Postgres, Storage |
| Extraction | Anthropic Claude |
| Transcription | OpenAI |
| Instagram media | yt-dlp (FFmpeg for audio) |

## Project layout

```
backend/          Flask API (port 5050)
  app.py       Routes for auth, extract, and recipes
  recipe.py    Extraction pipeline
  fetch.py     Instagram + website fetching
  store.py     Supabase persistence
  auth.py      Sign up, sign in, session
  transcribe.py
frontend/      React app (port 5173)
```

In development, Vite proxies `/auth`, `/extract`, and `/recipes` to the Flask server.

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (needed to pull audio from Instagram reels)
- A [Supabase](https://supabase.com) project
- API keys for [Anthropic](https://console.anthropic.com) and [OpenAI](https://platform.openai.com)

### 1. Supabase

Create a `recipes` table:

```sql
create table recipes (
  id text not null,
  user_id uuid not null references auth.users (id) on delete cascade,
  source text,
  created_at timestamptz,
  title text,
  ingredients jsonb,
  steps jsonb,
  thumbnail_url text,
  primary key (user_id, id)
);
```

Create a public Storage bucket named `thumbnails`.

### 2. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Create `backend/.env`:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
```

Use the service role key only on the server. It is required to create users and write recipes.

### 3. Frontend

```bash
cd frontend
npm install
```

For local development you do not need `VITE_API_URL`; the Vite proxy talks to Flask. Set it when the API is on a different origin:

```
VITE_API_URL=https://your-api.example.com
```

## Run locally

From the repo root, start the API:

```bash
source .venv/bin/activate
python backend/app.py
```

In another terminal, start the UI:

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Create an account, paste an Instagram reel or recipe page URL, and Unreel streams status updates while it extracts the recipe.

## API

All recipe and extract routes require `Authorization: Bearer <access_token>`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create an account |
| `POST` | `/auth/login` | Sign in |
| `POST` | `/auth/refresh` | Refresh the session |
| `GET` | `/auth/me` | Current user |
| `POST` | `/extract` | Extract a recipe (`url`, `source_type`: `instagram` or `website`). Streams NDJSON status, then the saved recipe |
| `GET` | `/recipes` | List saved recipes |
| `GET` | `/recipes/<id>` | Get one recipe |
| `DELETE` | `/recipes/<id>` | Delete a recipe |
