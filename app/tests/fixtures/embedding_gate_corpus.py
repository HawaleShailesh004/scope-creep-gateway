"""
Large labeled corpus of realistic Slack client/freelancer messages.

Each entry:
  - text: message as seen after extract_message_text()
  - label: expected gate decision ("skip" | "escalate")
  - safety_critical: if True and gate returns SKIP, that's a safety violation
  - category: for breakdown reporting
  - project: which fictional project context applies
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Label = Literal["skip", "escalate"]


@dataclass(frozen=True)
class CorpusEntry:
    text: str
    label: Label
    safety_critical: bool
    category: str
    project: str = "jewelry"


# ---------------------------------------------------------------------------
# Project briefs (used to build per-project reference vectors in benchmark)
# ---------------------------------------------------------------------------

PROJECTS: dict[str, dict] = {
    "jewelry": {
        "deliverables": [
            "Homepage redesign with hero banner and product grid",
            "About Us page",
            "Contact page with enquiry form",
            "Mobile-responsive layout across all pages",
            "Brand colour palette applied sitewide",
        ],
        "known_creep": [
            "Can you add an Our Story page?",
            "We also need a blog section for jewellery tips",
            "Could we get a second homepage variant for A/B testing?",
            "Add a ring size guide calculator",
        ],
    },
    "saas": {
        "deliverables": [
            "Admin dashboard with user management",
            "Analytics charts for MRR and churn",
            "Stripe billing integration",
            "Onboarding wizard for new tenants",
            "Email notification templates",
        ],
        "known_creep": [
            "Can we add a CSV export for all reports?",
            "We need SSO with Okta as well",
            "Add a white-label option for enterprise clients",
        ],
    },
    "mobile": {
        "deliverables": [
            "iOS login and signup screens",
            "Android home feed with infinite scroll",
            "Push notification setup",
            "Profile edit flow",
            "App Store screenshots and metadata",
        ],
        "known_creep": [
            "Can you also build the iPad version?",
            "We want dark mode on all screens",
            "Add Apple Watch companion app",
        ],
    },
    "brand": {
        "deliverables": [
            "Primary logo in SVG and PNG",
            "Brand guidelines PDF (colours, typography)",
            "Business card design",
            "Social media profile templates",
            "Letterhead design",
        ],
        "known_creep": [
            "Can you design packaging labels too?",
            "We need animated logo for the website",
            "Add merchandise mockups for t-shirts",
        ],
    },
}


def _e(text: str, label: Label, category: str, *, safety_critical: bool | None = None, project: str = "jewelry") -> CorpusEntry:
    sc = safety_critical if safety_critical is not None else (label == "escalate" and category not in {
        "deliverable_adjacent", "status_on_deliverable", "ambiguous_question",
    })
    return CorpusEntry(text=text, label=label, safety_critical=sc, category=category, project=project)


def build_corpus() -> list[CorpusEntry]:
    entries: list[CorpusEntry] = []

    # ---- ACKNOWLEDGMENTS & REACTIONS (must skip) ----
    acks = [
        "Thanks!", "Thank you so much", "Thx", "Ty!", "Cheers mate",
        "Ok", "Okay got it", "Kk", "Sounds good", "SG", "Perfect",
        "Great work", "Awesome", "Nice one", "Love it", "Looks good",
        "Lgtm", "Will do", "On it", "Done", "Noted", "Understood",
        "Makes sense", "Agreed", "Yep", "Sure thing", "No worries",
        "Congrats on the launch!", "Welcome to the channel",
        "Good morning team", "Good night", "Hi everyone", "Hey!",
        "That's exactly what we wanted", "Really happy with this",
        "Appreciate the quick turnaround", "You're the best",
        ":+1:", ":white_check_mark:", ":fire:", ":heart:", ":tada:",
        "👍", "🙏", "...", "!!!", "haha nice", "lol perfect",
        "Thanks, looks great!", "Perfect, appreciate it",
        "Ok that works for me", "Yes please go ahead with that",
    ]
    for t in acks:
        entries.append(_e(t, "skip", "ack"))

    # ---- PURE CHATTER / RELATIONSHIP (should skip via stage 2) ----
    chatter = [
        "Just checking in on progress",
        "How's everything going on your end?",
        "Hope you had a good weekend",
        "Let me know if you need anything from me",
        "No rush on this one",
        "Take your time",
        "We're not in a hurry",
        "Ping me when you have something to show",
        "Looking forward to seeing it",
        "Excited to see the next version",
        "The team is really happy so far",
        "Client loved the preview in our standup",
        "I'll be OOO Thursday and Friday",
        "Back on Monday if you need me",
        "Can we sync on a call next week? purely to align",
        "Sent you the brand assets via email",
        "Did you get the files I uploaded yesterday?",
        "Our CEO saw the WIP and was impressed",
        "Budget approval came through from finance",
        "Legal signed off on the contract",
        "When do you think the next update will be ready?",
        "How is it going?",
        "Any news on timing?",
        "Just wanted to say great work on this so far",
        "Really appreciate how responsive you've been",
        "Sorry for the delayed reply",
        "Catching up on messages now",
        "Happy new year!",
        "Hope the holidays were good",
    ]
    for t in chatter:
        entries.append(_e(t, "skip", "chatter"))

    # ---- EXPLICIT CREEP / WORK REQUESTS (must escalate, safety critical) ----
    explicit = [
        ("Can you add an Our Story page?", "jewelry"),
        ("Could we get a blog section too?", "jewelry"),
        ("Please add a ring size guide", "jewelry"),
        ("We need a store locator map on the site", "jewelry"),
        ("Can you also do Hindi language support?", "jewelry"),
        ("Add a wishlist feature for logged-in users", "jewelry"),
        ("thanks, can you also add dark mode", "jewelry"),
        ("Looks great — can you add testimonials on the homepage?", "jewelry"),
        ("One more round on the homepage please", "jewelry"),
        ("Please update the footer with our new address", "jewelry"),
        ("Could you change the font to something more premium?", "jewelry"),
        ("We want a popup for newsletter signup", "jewelry"),
        ("Can we add live chat widget?", "jewelry"),
        ("Also need Instagram feed embedded on homepage", "jewelry"),
        ("Can you build a CSV export for analytics?", "saas"),
        ("We need SSO with Okta", "saas"),
        ("Please add role-based permissions for admins", "saas"),
        ("Could you integrate HubSpot as well?", "saas"),
        ("Add bulk user import via CSV", "saas"),
        ("We want custom webhooks for enterprise tier", "saas"),
        ("Can you also build the iPad version?", "mobile"),
        ("Add dark mode to all screens", "mobile"),
        ("We need offline mode for the feed", "mobile"),
        ("Please add biometric login", "mobile"),
        ("Could we get an Apple Watch app too?", "mobile"),
        ("Can you design product packaging labels?", "brand"),
        ("We need an animated logo for the site", "brand"),
        ("Add merchandise mockups for t-shirts", "brand"),
        ("Please create billboard mockups as well", "brand"),
        ("Could you do menu designs for our cafe?", "brand"),
        ("pls add FAQ page", "jewelry"),
        ("pls ?", "jewelry"),
        ("while you're at it add a careers page", "jewelry"),
        ("on top of that we need a press kit section", "jewelry"),
        ("in addition can you set up Google Analytics 4", "jewelry"),
        ("let's add a video background to the hero", "jewelry"),
        ("what if we did a second homepage design option", "jewelry"),
        ("how about adding AR try-on for rings", "jewelry"),
        ("is it possible to add WhatsApp ordering", "jewelry"),
        ("I need a landing page for our new collection", "jewelry"),
        ("We'd like a custom 404 page with brand illustration", "jewelry"),
        ("Can we swap the contact form for Typeform?", "jewelry"),
        ("Please remove the old blog section and rebuild it", "jewelry"),
        ("Delete the placeholder images and use ours", "jewelry"),
        ("New page for store opening event next month", "jewelry"),
        ("Another version of the logo in monochrome please", "brand"),
        ("Revise the business card — phone number changed", "brand"),
        ("Redo the social templates with new colours", "brand"),
    ]
    for t, proj in explicit:
        entries.append(_e(t, "escalate", "explicit_request", safety_critical=True, project=proj))

    # ---- SOFT / IMPLICIT CREEP (must escalate) ----
    soft = [
        ("We should probably add a testimonials section", "jewelry"),
        ("I was thinking maybe a jewellery care guide page", "jewelry"),
        ("It would be nice to have customer reviews on product pages", "jewelry"),
        ("Maybe we could include a virtual try-on feature", "jewelry"),
        ("Would be cool to have a loyalty points section", "jewelry"),
        ("Thinking we might need a B2B wholesale portal", "jewelry"),
        ("Probably should add multi-currency support", "jewelry"),
        ("Might need a chatbot for common questions", "saas"),
        ("Was wondering if we could do Slack integration", "saas"),
        ("Perhaps add a audit log for compliance", "saas"),
    ]
    for t, proj in soft:
        entries.append(_e(t, "escalate", "soft_creep", safety_critical=True, project=proj))

    # ---- DELIVERABLE STATUS / SCOPE QUESTIONS (escalate — need AI) ----
    deliverable_q = [
        ("Is our story page designed?", "jewelry"),
        ("What about the contact form — is that done?", "jewelry"),
        ("Any update on the mobile layout?", "jewelry"),
        ("Has the About page been started yet?", "jewelry"),
        ("Is the enquiry form working on mobile?", "jewelry"),
        ("Did you finish the hero banner?", "jewelry"),
        ("Where are we with the colour palette rollout?", "jewelry"),
        ("Is Stripe integration complete?", "saas"),
        ("What's the status on the onboarding wizard?", "saas"),
        ("Are push notifications set up yet?", "mobile"),
        ("Is the logo finalized in all formats?", "brand"),
        ("The homepage looks really polished now", "jewelry"),  # deliverable-adjacent praise
        ("Nice update on the hero banner", "jewelry"),  # mentions deliverable work
        ("Contact page is missing the map we discussed", "jewelry"),
        ("The footer still has placeholder text", "jewelry"),
        ("About page copy doesn't match what we sent", "jewelry"),
    ]
    for t, proj in deliverable_q:
        entries.append(_e(t, "escalate", "deliverable_question", safety_critical=False, project=proj))

    # ---- REVISION REQUESTS (escalate, safety critical) ----
    revisions = [
        "Can we try a different layout for the hero?",
        "The blue feels too dark — lighter shade?",
        "Font looks a bit small on mobile",
        "Spacing between sections feels tight",
        "Can you move the CTA above the fold?",
        "Logo needs to be bigger on mobile header",
        "Product grid should be 3 columns not 4",
        "Navigation menu order should change",
        "Button colour doesn't match brand guide",
        "Images are loading too slowly — optimize?",
    ]
    for t in revisions:
        entries.append(_e(t, "escalate", "revision", safety_critical=True))

    # ---- AMBIGUOUS (escalate to be safe — AI decides) ----
    ambiguous = [
        "Thoughts on the latest mockup?",
        "What do you think about option B?",
        "See attached — let me know",
        "Compare these two approaches",
        "Which direction do you prefer?",
        "Flagging this for your review",
        "Not sure if this is in scope but sharing anyway",
        "Our competitor has this feature — thoughts?",
    ]
    for t in ambiguous:
        entries.append(_e(t, "escalate", "ambiguous", safety_critical=False))

    # ---- EDGE CASES ----
    edges = [
        _e("", "skip", "edge_empty"),
        _e("   ", "skip", "edge_whitespace"),
        _e("k", "skip", "edge_short_ack"),
        _e("ok", "skip", "edge_short_ack"),
        _e("dark mode too", "escalate", "edge_short_creep", safety_critical=True),
        _e("blog?", "escalate", "edge_short_creep", safety_critical=True),
        _e("Thanks — when's the next milestone?", "skip", "ack_with_timing"),  # timing not request
        _e("Great! Can you share the staging link?", "escalate", "ack_with_ask", safety_critical=True),
    ]
    entries.extend(edges)

    # ---- MORE REALISTIC SLACK NOISE ----
    slack_noise = [
        "Following up on my last message",
        "Bumping this thread",
        "Any thoughts when you get a chance",
        "Shared in the Figma link above",
        "Left comments on the mockup",
        "Approved the latest version in email",
        "Forwarding this to our marketing lead",
        "Looping in @sarah from our side",
        "Standup update: client is happy with direction",
        "Quick note — board meeting went well",
        "Invoice received, thanks",
        "Payment sent via Razorpay",
        "Signed the SOW copy you sent",
        "Traveling this week, slower to respond",
        "Out sick today, back tomorrow",
        "On a call, will reply later",
        "Reviewed the staging site on my phone",
        "Showed it to the founder — big thumbs up",
        "We're presenting this to investors Friday",
        "Demo went really well yesterday",
    ]
    for t in slack_noise:
        entries.append(_e(t, "skip", "chatter"))

    # ---- MULTI-PROJECT CLIENT MIX (same patterns, different domains) ----
    cross_project = [
        _e("Can you add two-factor auth?", "escalate", "explicit_request", safety_critical=True, project="saas"),
        _e("Push notification badge count is wrong", "escalate", "revision", safety_critical=True, project="mobile"),
        _e("Letterhead PDF export looks blurry", "escalate", "revision", safety_critical=True, project="brand"),
        _e("Dashboard load time is too slow", "escalate", "revision", safety_critical=True, project="saas"),
        _e("Just saw the beta on TestFlight — awesome", "skip", "chatter", project="mobile"),
        _e("Brand guide colours look perfect in print", "skip", "chatter", project="brand"),
        _e("Analytics chart tooltips are confusing", "escalate", "revision", safety_critical=True, project="saas"),
        _e("Could you add Tamil language on the site?", "escalate", "explicit_request", safety_critical=True, project="jewelry"),
        _e("We need UPI payment option at checkout", "escalate", "explicit_request", safety_critical=True, project="jewelry"),
        _e("EMI calculator on product pages please", "escalate", "explicit_request", safety_critical=True, project="jewelry"),
    ]
    entries.extend(cross_project)

    return entries


def expand_for_load_test(corpus: list[CorpusEntry], multiplier: int = 5) -> list[CorpusEntry]:
    """Repeat corpus with light paraphrase suffix for throughput testing."""
    if multiplier <= 1:
        return corpus
    out = list(corpus)
    suffixes = ["", " — following up", " (async)", " today", " pls"]
    for i in range(1, multiplier):
        for entry in corpus:
            suffix = suffixes[i % len(suffixes)]
            if suffix and not entry.text.endswith(suffix):
                text = entry.text + suffix
            else:
                text = entry.text
            out.append(CorpusEntry(
                text=text,
                label=entry.label,
                safety_critical=entry.safety_critical,
                category=entry.category,
                project=entry.project,
            ))
    return out
