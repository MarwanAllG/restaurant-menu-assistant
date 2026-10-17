# Restaurant Menu Assistant

A conversational restaurant menu assistant built with Python, Chainlit, LangChain,
LangGraph and SQLite. It recommends dishes from a fixed 50-item menu and remembers
preferences across conversations.

## How it works

1. Authenticate the user and check conversation ownership.
2. Load saved preferences and extract proposed memory edits/current-request constraints.
3. Validate supporting evidence and save updates transactionally.
4. Let one agent answer naturally using `search_menu`, `get_menu_items` and `respond`.
5. Validate selected IDs and constraints; render exact dish details from `menu.json`.

The final response schema contains only `reply` and `item_ids`. Greetings and memory
questions need no menu search. Python enforces menu eligibility and displays prices,
ingredients, images and preference-based explanations from the authoritative records.

Saved preferences and temporary constraints are separate. A numeric request budget
such as “tonight, up to 50 SAR” overrides a usual 30 SAR default for the current
conversation without changing the saved value. New chats restore the saved default.
Saved dietary restrictions and allergies remain enforced independently.

## Run locally

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen --no-dev
cp .env.example .env
uv run --no-dev python scripts/configure_accounts.py
```

The setup utility prompts for two usernames and passwords, then writes password
hashes and an authentication secret to the ignored `.env`. Set `OPENROUTER_API_KEY`
in that file. The default model is `deepseek/deepseek-v4.1-flash` through OpenRouter.

```sh
DEBUG=false uv run --no-dev python -m chainlit run app.py --host 127.0.0.1 --port 8000
```

Open http://localhost:8000 and sign in with the accounts you configured. The optional
`--generate` argument to the setup utility creates random passwords in a private,
ignored `data/local-test-accounts.txt` file. No credentials are included in this repo.

Use **New chat** for a new conversation with the same saved preferences. Resume chats
through the history sidebar. **Remembered preferences** or `/preferences` displays
one updating block; natural-language memory questions are answered by the agent.
Corrections and forgetting are supported. “Start a new request” clears temporary
constraints while preserving saved preferences.

## Code walkthrough

| File | Responsibility |
| --- | --- |
| `app.py` | Chainlit entry point, authentication hooks, messages and UI actions |
| `core/workflow.py` | LangGraph coordination, state and checkpoint persistence |
| `core/schemas.py` | Validated memory edits, constraints and two-field response |
| `core/repository.py` | SQLite users, preferences, events and retry protection |
| `core/agent.py` | One conversational agent with two menu tools and a response tool |
| `core/menu.py` | Menu loading, filtering, preference ranking and price sorting |
| `core/provider.py` | OpenRouter structured extraction, tool calls and controlled errors |
| `core/render.py` | Authoritative dish cards and preference display |
| `core/data_layer.py` | Ownership-checked Chainlit history from saved checkpoints |
| `core/auth.py` | PBKDF2 password hashing and verification |
| `core/config.py` | Environment configuration |
| `scripts/configure_accounts.py` | Private account setup |
| `.chainlit/`, `public/` | Interface configuration, translations and visual assets |

## Deployment

Build the supplied Docker image and configure the hosting service to route traffic
to port 8000. Run one instance with a writable persistent volume mounted at `/data`.
Configure `OPENROUTER_API_KEY`, `TEST_ACCOUNTS_JSON` and a stable
`CHAINLIT_AUTH_SECRET` through the hosting service. Set `APP_URL` to the deployed
HTTPS origin and `CHAINLIT_COOKIE_SAMESITE=none` for HTTPS deployment.
The application requires WebSocket support and durable storage for both SQLite
databases under `DATA_DIR` (the Docker image defaults to `/data`).

## Scope

The public repository contains the runtime, setup utility and Docker deployment files.
Notebooks, test suites, raw recipe backups, local databases and credentials are omitted.

This is a demo menu: prices and annotations are fictional. Filtering uses the
`allergens` list and ignores `allergenStatus`. Nutrition, portions, certification,
customization, ordering, payment and inventory are not supplied. Brief generated replies
remain fallible even though selected IDs and detailed cards are validated.

SQLite suits this single-instance demo. Higher traffic or multiple instances would
require a different storage/concurrency design. Provider calls may fail or reach an
output limit; controlled errors preserve saved data. Deployment files are prepared;
no hosted deployment is claimed.
