# ScopeGuard - Freelancer Guide

**What this app does (in one line):**  
It watches your client project channel, quietly warns _you_ when something looks out of scope, and helps you absorb small asks or send a change order - without awkwardness in front of the client.

**Names you’ll see**

- **ScopeGuard** - product name (App Home, docs, judges, video)
- **Scope Health** - bot display name in channels + canvas health metric (softer for clients)
- **Keystone Digital Studio** - studio name on `/studio-report` and seeded summaries

Private alerts go only to **you**. Clients never see the warning cards.

---

## Before you start

1. Invite **@Scope Health** to the project channel.
2. Make sure the **client** is set correctly in the brief (only their messages are checked).
3. After setup, a short **disclosure** posts in the channel (transparency). Scope checks stay private to you.

---

## Slash commands

Use these in a **project channel** (unless noted).

### Setup & brief

| Command         | What it does                                        | When to use                        |
| --------------- | --------------------------------------------------- | ---------------------------------- |
| `/setup-brief`  | Creates the project brief + **Scope Health** canvas | First time in a new client channel |
| `/update-brief` | Edit deliverables, budget, deadline                 | Scope changed mid-project          |
| `/import-brief` | Pull scope from a SOW / brief document              | You already have a written brief   |

**Tip:** After `/setup-brief`, open the channel’s **Canvas** tab - that’s your live Scope Health board.

---

### Catching & billing extra work

| Command         | What it does                         | When to use                                               |
| --------------- | ------------------------------------ | --------------------------------------------------------- |
| `/change-order` | Manually draft a change order        | You want to bill something yourself (no auto-flag needed) |
| `/absorbed`     | Shows “let it slide” / goodwill work | Check how much free work you’ve given                     |

**When the app detects creep**, you get a **private** card with choices:

- **Generate Change Order** - cost + timeline draft → edit → post
- **Let it slide** - logged as absorbed (keeps score)
- **Not scope creep** - dismiss false alarm
- **Draft reply** - client-facing message (posts **as you**, not as the bot)

---

### Insights (portfolio brain)

| Command          | What it does                                             | When to use                         |
| ---------------- | -------------------------------------------------------- | ----------------------------------- |
| `/client-report` | Pattern stats for a client                               | “Is this client always creeping?”   |
| `/studio-report` | Studio-wide absorbed hours, billing, who needs attention | Weekly check-in / demo “depth” beat |

---

### Pause / resume

| Command              | What it does                | When to use                       |
| -------------------- | --------------------------- | --------------------------------- |
| `/scope-gateway-off` | Pause watching this channel | Sensitive chat, or you want quiet |
| `/scope-gateway-on`  | Turn watching back on       | Ready to monitor again            |

---

## Message shortcuts (right‑click a message)

| Shortcut                       | What it does                                          |
| ------------------------------ | ----------------------------------------------------- |
| **Flag as scope change**       | Manually flag that message and open change-order flow |
| **Import brief from document** | Extract scope from an attached / linked brief message |

---

## Typical day (simple flow)

```
1. /setup-brief          → brief + canvas live
2. Client chats as usual
3. Out-of-scope ask      → private warning (only you)
4. You choose            → absorb  OR  change order + reply
5. Canvas updates        → Scope Health stays honest
6. /studio-report        → see the whole book of work (optional)
```

---

## Privacy cheat-sheet

| Thing                                           | Client sees?          | You see?      |
| ----------------------------------------------- | --------------------- | ------------- |
| Scope warning card                              | No                    | Yes (private) |
| Disclosure / “Scope Health is active”           | Yes                   | Yes           |
| Change order in thread                          | Yes                   | Yes           |
| Your drafted reply                              | Yes (as **you**)      | Yes           |
| Canvas Scope Health                             | Yes (in channel)      | Yes           |
| `/client-report`, `/studio-report`, `/absorbed` | No (ephemeral to you) | Yes           |

---

## Quick troubleshooting

| Problem                        | Try this                                                                              |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| No warnings on client messages | Is classification on? (`/scope-gateway-on`). Is the poster the **registered client**? |
| Warning for your own message   | Normal skip - only the client is classified                                           |
| Canvas didn’t refresh          | Re-open the Canvas tab; check you’re signed in with canvas permissions                |
| Want silence for a bit         | `/scope-gateway-off`                                                                  |

---

_Built for freelancers who want clear scope - and paid extras - without fighting in the channel._
