# ScopeGuard — For judges

Short guide to what matter deep in the product — trust, goodwill scoreboard, and why this is Slack-native.

**Product:** ScopeGuard  
**In-channel bot + canvas metric:** Scope Health  
**Demo studio:** Keystone Digital Studio  

Diagram: [architecture.svg](./architecture.svg) · deeper stack: [../ARCHITECTURE.md](../ARCHITECTURE.md) · user flow: [../FREELANCER_GUIDE.md](../FREELANCER_GUIDE.md)

---

## What to try (5 minutes)

1. Open `#acme-website` as the client (Priya).
2. Post something clearly out of scope, e.g. _“btw could you pop a little newsletter signup in the footer?”_
3. Switch to the freelancer view → private ephemeral warning (client sees nothing).
4. Choose **Let it slide** or **Generate Change Order**.
5. Open the channel **Canvas** → Scope Health updates.
6. In `#studio-hq`, run `/studio-report` → Lumen stressed, Verde clean, Acme mid-book.

Sample SOW for `/import-brief`: [`../demo/SAMPLE_SOW_ACME.txt`](../demo/SAMPLE_SOW_ACME.txt).

---

## The three ideas that differentiate this

### 1. Privacy split (relationship, not surveillance)

| Who | Sees |
| --- | --- |
| **Freelancer** | Out-of-scope warning, RTS context, Bill / Slide / Draft reply |
| **Client** | Never the accusation. Shared Scope Health canvas + public change-order card (details only) |
| **Client (ephemeral)** | Approve & Pay / Simulate payment — only when they’re the designated client |

Presence is disclosed in-channel. Judgment stays private. That inversion is deliberate Slack policy + relationship design — not a demo shortcut.

### 2. Goodwill scoreboard (the real moat)

Detection alone is common. ScopeGuard’s differentiator:

- **Let it slide** → logged as absorbed hours + value
- Small/trivial out-of-scope can **auto-absorb** without interrupting
- Portfolio (`/studio-report`, App Home) shows **who absorbs the most** across clients

Seeded demo: Lumen ~7h absorbed + pending COs (stressed); Verde 100%; Acme healthy until live creep. Almost no tool tracks unpaid goodwill across a book of work.

### 3. Draft and post as you

Change orders and client replies are authored with ScopeGuard, then posted **as the freelancer** (user token) — not as a third bot voice in the client channel. ScopeGuard stays the advocate behind the curtain.

---

## Why only Slack (three load-bearing primitives)

| Primitive | Role |
| --------- | ---- |
| **Events API** | Ambient listen — catch the ask the moment it lands |
| **MCP + Canvas** | Living scope-of-record (brief + Scope Health); `canvases.edit` keeps it honest |
| **RTS** | Enrich warnings with channel history (“we touched on this before”) |

Without ambient events + shared canvas + permission-aware history, this is just another inbox alert — not an in-channel scope advocate.

---

## Pipeline (one glance)

```
Client message
  → pre-filter / disclosure / client-only
  → local embedding gate (SKIP | ESCALATE only — never a scope verdict)
  → Groq · Llama 3.3 70B classifier (size-aware)
  → severity router (auto-absorb small | warn significant)
  → RTS prior-mention (optional)
  → freelancer-only warning
  → absorb | change order | draft reply
  → Supabase + Scope Health canvas rebuild
```

Full module map, data model, locks, and limitations: [ARCHITECTURE.md](../ARCHITECTURE.md).

---

## Trust & data posture (review-ready)

- Channel disclosure on setup; bot intro on join
- Unflagged chatter is not stored as scope decisions
- Retention purge for expired stored message text
- No model training claim on workspace channel data
- User-facing UI never names LLM providers — only architecture docs do

---

## Naming cheat sheet

| Name | Where |
| ---- | ----- |
| **ScopeGuard** | App Home, README, Devpost, this repo |
| **Scope Health** | Bot display name, canvas title / health metric |
| **Keystone Digital Studio** | `STUDIO_NAME` / studio report |
