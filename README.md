# Scope Creep Gateway

Catch scope creep the moment it happens — inside your Slack project channels.

Scope Creep Gateway is a [Bolt for Python](https://docs.slack.dev/tools/bolt-python/) Slack app built for freelancers. It watches client project channels, compares every message against an agreed brief, and **privately** flags out-of-scope asks before they become unpaid work. When scope expands, it drafts change orders with cost and timeline, posts them in-thread for the client, and keeps a live **Scope Health** canvas up to date.

**Pitch:** Scope creep gets caught at the moment it happens, not at invoice time.

For system design, data flow, and module reference, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## What it does

1. **Project setup** — Capture an agreed brief and create a Scope Health canvas in the channel
2. **Ambient listening** — Classify client messages against the brief (local embedding gate + AI classifier)
3. **Private warnings** — Alert the freelancer when scope may have expanded; the client sees nothing
4. **Change orders** — AI-drafted COs with cost and timeline, editable before posting
5. **Scope Health canvas** — Budget, absorbed work, pending change orders, and change log
6. **Client intelligence** — Cross-project patterns and absorbed-work summaries

---

## Prerequisites

| Requirement | Notes |
| ----------- | ----- |
| Python 3.12+ | Tested on 3.13 |
| Slack app | Socket Mode enabled; see [Slack API](https://api.slack.com/apps) |
| Supabase project | Postgres persistence — run `app/db/schema.sql` and migrations |
| Anthropic API key | Scope classifier and change-order drafting |
| Slack user token | Canvas create/update and Real-Time Search (RTS) |

---

## Quick start

```bash
cd app
cp .env.sample .env
pip install -r requirements.txt
python app.py
```

Deploy manifest and scope changes to Slack:

```bash
cd app
slack app deploy
```

---

## Environment variables

Copy `app/.env.sample` to `app/.env` and configure:

| Variable | Required | Purpose |
| -------- | -------- | ------- |
| `SLACK_BOT_TOKEN` | Yes | Bot token (`xoxb-…`) |
| `SLACK_APP_TOKEN` | Yes | App-level token for Socket Mode (`xapp-…`) |
| `SLACK_USER_TOKEN` | Yes | User token for canvas API + RTS |
| `SUPABASE_URL` | Yes | Database URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key for writes |
| `ANTHROPIC_API_KEY` | Yes | AI classifier and CO drafter |
| `STRIPE_PAYMENT_LINK_URL` | No | Payment link on change-order cards |
| `DEMO_MODE` | No | `true` (default) shows simulate-payment button |

Run database migrations in Supabase SQL Editor before first use:

- `app/db/schema.sql`
- `app/db/migrations/002_tier1_v2.sql`

---

## Slash commands

| Command | Description |
| ------- | ----------- |
| `/setup-brief` | Define the project brief and create the Scope Health canvas |
| `/update-brief` | Edit the agreed scope and refresh the canvas |
| `/import-brief` | Extract scope from a pasted SOW or brief document |
| `/change-order` | Manually create a change order |
| `/absorbed` | Summary of let-it-slide and auto-absorbed work |
| `/client-report` | Client-level scope pattern stats |
| `/scope-gateway-off` | Pause classification (freelancer only) |
| `/scope-gateway-on` | Resume classification |

## Message shortcuts

| Shortcut | Description |
| -------- | ----------- |
| **Flag as scope change** | Flag any message and draft a change order |
| **Import brief from document** | Extract scope from a document message |

---

## Typical workflow

1. Freelancer creates a project channel, invites the bot and client
2. Run `/setup-brief` — fill in deliverables, budget, deadline, client
3. Bot posts a visible disclosure and creates the Scope Health canvas
4. Client sends messages — only the designated client is classified
5. Out-of-scope asks trigger a **private** warning to the freelancer with actions:
   - **Generate Change Order** — AI drafts cost/timeline; freelancer edits and posts
   - **Let it slide** — logged as absorbed goodwill
   - **Not scope creep** — dismissed as false positive
6. Posted change orders appear in-thread; client can approve/pay (stub flow in demo mode)
7. Paid change orders fold into the effective brief; canvas updates automatically

**Manual fallback:** Right-click any message → **Flag as scope change** if the classifier misses something.

---

## Repository layout

```
scope-creep-gateway/
├── README.md           # This file — setup and usage
├── ARCHITECTURE.md     # System design and module reference
├── LICENSE
└── app/                # Slack application source
    ├── app.py          # Entry point (Socket Mode)
    ├── manifest.json   # Slack app manifest
    ├── classifier.py   # AI scope classifier
    ├── listeners/      # Commands, events, actions, views
    ├── services/       # Business logic
    ├── db/             # Schema and Supabase client
    └── tests/          # Unit tests
```

---

## Tests

```bash
cd app
pytest tests/ -q
```

CI runs tests and ruff on every push to `main`.

The embedding gate includes corpus-based safety tests (`tests/test_embedding_gate_corpus.py`) that require `sentence-transformers` (~80 MB model, lazy-loaded).

---

## OAuth / HTTP mode

For app distribution with OAuth instead of Socket Mode, use `app/app_oauth.py`. See `.env.sample` for OAuth-specific variables.

---

## Privacy and trust

- Classification runs only after visible channel disclosure
- Warnings are **ephemeral to the freelancer** — clients never see scope flags
- Message text for resolved items is purged on a retention schedule
- App Home includes a transparency block explaining what is read and stored

---

## License

See [LICENSE](./LICENSE).
