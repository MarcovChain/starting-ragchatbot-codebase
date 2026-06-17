# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# First-time setup: copy and fill in your API key
cp .env.example .env

# Start the server (from repo root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

The server loads all `.txt` files from `docs/` into ChromaDB on startup, skipping any courses already indexed.

## Dependency Management

Always use `uv` — never `pip` directly.

```bash
uv add <package>      # add a dependency
uv sync               # install all dependencies
uv run <command>      # run any command in the project environment
```

Python 3.13 required (see `.python-version`).

## Architecture

**Agentic RAG pattern**: Claude decides whether to call the vector search tool rather than always pre-fetching context. This means every query makes at least one Claude API call, and course-specific questions make two (one to decide to search + one to synthesize results).

**Request flow**:
```
frontend/script.js
  → POST /api/query (app.py)
  → RAGSystem.query() (rag_system.py)         # orchestrator
  → AIGenerator.generate_response()           # 1st Claude call w/ tool
    → [if tool_use] CourseSearchTool.execute()
      → VectorStore.search()                  # ChromaDB lookup
    → AIGenerator._handle_tool_execution()    # 2nd Claude call w/ results
  → SessionManager.add_exchange()             # persist history
  → return { answer, sources, session_id }
```

**ChromaDB has two collections**:
- `course_catalog` — one document per course (title, instructor, lesson links). Used for fuzzy course-name resolution.
- `course_content` — 800-char sentence-based chunks with `course_title` and `lesson_number` metadata. Used for semantic content search.

**Session history** is in-memory only (lost on server restart). Configured to keep the last 2 exchanges (`MAX_HISTORY` in `config.py`), passed as plain text appended to the system prompt.

## Course Document Format

Files in `docs/` must follow this structure for the parser in `document_processor.py` to extract lessons correctly:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <title>
Lesson Link: <url>
...lesson content...

Lesson 2: <title>
...
```

The course title doubles as the unique ID in ChromaDB — duplicate titles will be skipped on reload.

## Key Configuration (`backend/config.py`)

| Setting | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for all generation |
| `CHUNK_SIZE` | `800` | Max chars per vector chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `MAX_RESULTS` | `5` | Chunks returned per search |
| `MAX_HISTORY` | `2` | Conversation exchanges remembered |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence path (relative to `backend/`) |
