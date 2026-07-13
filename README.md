# ScopeGuard

Catch scope creep the moment it happens - inside your Slack project channels.

**ScopeGuard** is a [Bolt for Python](https://docs.slack.dev/tools/bolt-python/) Slack app built for freelancers. It watches client project channels, compares every message against an agreed brief, and **privately** flags out-of-scope asks before they become unpaid work. When scope expands, it drafts change orders with cost and timeline, posts them in-thread for the client, and keeps a live **Scope Health** canvas up to date.

**Names:** **ScopeGuard** is the product (App Home, docs, judges). **Scope Health** is the in-channel bot name and the canvas health metric.

**Studio demo cast:** Keystone Digital Studio (`STUDIO_NAME`).

**Pitch:** Scope creep gets caught at the moment it happens, not at invoice time.

**Docs for judges:** [docs/FOR_JUDGES.md](./docs/FOR_JUDGES.md) · [docs/architecture.svg](./docs/architecture.svg) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [FREELANCER_GUIDE.md](./FREELANCER_GUIDE.md)

---

## What it does

1. **Project setup** - Capture an agreed brief and create a Scope Health canvas
2. **Ambient listening** - Classify client messages against the brief (local gate + ScopeGuard classifier)
3. **Private warnings** - Alert the freelancer only; the client sees nothing
4. **Change orders** - ScopeGuard-drafted COs with cost and timeline, editable before posting
5. **Scope Health canvas** - Budget, absorbed work, pending change orders, and change log
6. **Client intelligence** - Cross-project patterns and absorbed-work summaries

---

## Quick start

```bash
cd app
cp .env.sample .env
# fill Slack, Supabase, and keys listed in .env.sample
python app.py
```

Socket Mode ON for local demo. Seed:

```bash
python scripts/seed_keystone.py
```

Channels: `#acme-website`, `#lumen-landing`, `#verde-brand`, `#studio-hq`.

---

## Slash commands

| Command | Purpose |
| ------- | ------- |
| `/setup-brief` | Define brief + canvas |
| `/import-brief` | Import from SOW / document |
| `/update-brief` | Edit deliverables, budget, deadline |
| `/change-order` | Manual change order |
| `/absorbed` | Absorbed (let-it-slide) summary |
| `/client-report` | Client pattern stats |
| `/studio-report` | Studio capacity + billing |
| `/scope-gateway-off` | Pause classification |
| `/scope-gateway-on` | Resume classification |
