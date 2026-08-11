# Spotify AI Playlist Generator

An AI-powered Spotify playlist generator designed to understand nuanced prompts,
learn a user's music taste, balance familiar tracks with discovery, and create
playlists with smooth musical transitions. The long-term goal is to build a
recommendation engine that owns the core selection and scoring logic while using
AI to interpret prompts and support decision-making.

## Current Status

This project is in early development. It currently provides a minimal FastAPI
application with a health-check endpoint and an automated API test.

## Product Vision

The finished application should:

- Understand detailed, natural-language playlist requests.
- Learn individual listening preferences over time.
- Balance favorite music with relevant discoveries.
- Order tracks to create smooth musical transitions.
- Keep recommendation and scoring logic within the application instead of
  delegating the entire product to a large language model.

## Tech Stack

- Python 3.13
- FastAPI
- Uvicorn
- pytest
- httpx

## Local Setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/apelluri12/spotify-ai-playlist.git
cd spotify-ai-playlist
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## Running the API

Start the local development server:

```bash
uvicorn app.main:app --reload
```

Once the server starts, open:

- API root: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

The API root does not have a route yet, so it currently returns `404 Not Found`.

## Running Tests

Run the test suite from the repository root:

```bash
python -m pytest -v
```

## Roadmap

- Spotify authentication using Authorization Code with PKCE
- Spotify playlist creation and track management
- AI-assisted prompt parsing
- Recommendation and playlist-scoring engines
- User preference learning and feedback loops
- Web interface
- Docker-based development and deployment
- GitHub Actions CI/CD
- Cloud deployment
