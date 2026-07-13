"""
embedding_gate.py - cheap local pre-classifier that decides whether a message
needs the full AI scope classifier, or is obviously not a work request and
can be skipped.

CORE SAFETY INVARIANT
---------------------
This gate NEVER produces a scope verdict. It returns exactly one of:
    - GateDecision.SKIP      → message is confidently NOT a work request; do not
                               spend a AI call, do not warn, do nothing.
    - GateDecision.ESCALATE  → send to the existing AI classify() path.

A wrong SKIP must only ever be "we ignored a non-request". It must NEVER be
"we missed a scope-creep request". Every rule below is biased toward ESCALATE.
When in doubt, escalate. Errors escalate. Novel text escalates. Anything that
looks like a request escalates - even if it's topically similar to existing work
(because "add a SECOND homepage" is similar to a "homepage" deliverable but is
still creep).

TWO STAGES (both local, both fast):
    Stage 1 - structural filter (regex/keywords, microseconds):
        confidently drop obvious non-requests (thanks/ack/emoji/status) and
        confidently flag obvious requests (imperatives / "can you" / "please add").
    Stage 2 - embedding novelty router (~5-15ms, only if Stage 1 is unsure):
        embed the message, compare to cached reference clusters, and SKIP only
        when it is clearly closest to the "not a request" cluster AND not novel.

Design notes:
    - Embeddings are local (sentence-transformers). No network, no per-message API.
    - The model is loaded once, lazily, and reused.
    - Reference vectors are cached per project (deliverables change per project;
      the generic clusters are shared and cached once).
    - Everything degrades safely: if the model can't load, Stage 2 is disabled and
      every Stage-1-unsure message escalates. The gate can only ever make the
      system SPEND MORE, never miss creep, if it breaks.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision type
# ---------------------------------------------------------------------------

class GateDecision(str, Enum):
    SKIP = "skip"          # not a work request - do nothing, no AI call
    ESCALATE = "escalate"  # run the existing AI classifier


@dataclass
class GateResult:
    decision: GateDecision
    stage: str              # "stage1_nonrequest" | "stage1_request" | "stage2_skip"
                            # | "stage2_escalate" | "fallback_escalate"
    reason: str             # human-readable, for logging/telemetry
    similarity: Optional[float] = None  # best "not-a-request" sim, if computed


# ---------------------------------------------------------------------------
# Tunable thresholds - all conservative (bias to ESCALATE)
# ---------------------------------------------------------------------------

@dataclass
class GateConfig:
    # Stage 2 only skips when the message is BOTH:
    #   - clearly closest to the non-request cluster (sim >= skip_nonrequest_sim), AND
    #   - not meaningfully close to any deliverable/creep cluster
    #     (margin over those clusters >= skip_margin)
    skip_nonrequest_sim: float = 0.58   # tuned on corpus; still conservative
    skip_margin: float = 0.06           # margin over work clusters
    # If a message is novel (far from EVERYTHING we know), escalate - it's unusual,
    # and unusual is exactly when we want AI's judgment.
    novelty_floor: float = 0.28         # slightly lower - expanded exemplars cover more
    min_words_for_stage2: int = 3       # very short survivors already handled in stage 1
    nonrequest_top_k: int = 3           # mean of top-k exemplar sims (smoother than max-only)


# ---------------------------------------------------------------------------
# Stage 1 - structural filter (no embeddings, microseconds)
# ---------------------------------------------------------------------------

# Obvious NON-REQUEST patterns. High precision - only drop what is unmistakably
# not a request for work. Err toward NOT matching (fall through to stage 2/escalate).
_ACK_ONLY = re.compile(
    r"^\s*("
    r"thanks?(\s+(so much|a lot|again|mate|team|everyone))?"
    r"|thank you(\s+(so much|again|everyone))?"
    r"|thx|ty|tysm|cheers(\s+mate)?|"
    r"ok(ay)?(\s+got it)?|kk|k|got it|sounds good|sg|perfect|great|awesome|"
    r"nice(\s+one)?|cool|looks good|looks great|lgtm|love it|amazing|beautiful|excellent|"
    r"great work|good work|nice work|well done|"
    r"will do|on it|done|noted|understood|makes sense|agreed|yep|yes|no|nope|"
    r"sure(\s+thing)?|no worries|"
    r"good morning(\s+team)?|good night|good evening|gm|gn|"
    r"hi(\s+everyone)?|hello|hey|welcome(\s+to the channel)?|"
    r"congrats(\s+on the launch)?|congratulations|"
    r"haha nice|lol perfect|you'?re the best"
    r")[\s!.,😀-🫿👍🙏✅🔥💯]*$",
    re.IGNORECASE,
)

# Multi-word acks / compliments that aren't single-token _ACK_ONLY matches.
_ACK_PHRASE = re.compile(
    r"^\s*("
    r"thanks?,?\s+looks great"
    r"|really happy with (this|it|the result)"
    r"|that'?s exactly what we wanted"
    r"|appreciate the quick turnaround"
    r"|perfect,?\s+appreciate it"
    r"|ok that works for me"
    r"|yes please go ahead with that"
    r"|thanks so much for this"
    r")[\s!.,]*$",
    re.IGNORECASE,
)

# Obvious check-in / social / admin chatter - not scope requests.
_CHATTER_STATUS = re.compile(
    r"^\s*("
    r"just checking in( on progress)?"
    r"|how is it going|how'?s it going|how are things|how'?s everything going"
    r"|when do you think .{0,60}(ready|will be|timeline)"
    r"|any news on timing"
    r"|let me know if you need anything( from me)?"
    r"|following up on my last message"
    r"|bumping this thread"
    r"|take your time|no rush|not in a hurry|no rush on this one|we'?re not in a hurry"
    r"|back on monday|catching up on messages now"
    r"|hope the holidays were good|hope you had a good weekend|happy new year"
    r"|our ceo saw the wip|budget approval came through|legal signed off"
    r"|did you get the files i uploaded|any thoughts when you get a chance"
    r"|just wanted to say great work|really appreciate how responsive"
    r"|i'?ll be ooo|out sick today|on a call|traveling this week"
    r"|invoice received|payment sent|signed the sow"
    r"|demo went really well|board meeting went well"
    r"|shared in the figma link|left comments on the mockup"
    r")[\s?!.,]*$",
    re.IGNORECASE,
)

# Pure reaction: emoji / punctuation only (after text extraction).
_EMOJI_OR_PUNCT_ONLY = re.compile(r"^[\s\W_]*$", re.UNICODE)
_SLACK_EMOJI_ONLY = re.compile(r"^(\s*:[a-z0-9_+\-]+:\s*)+$", re.IGNORECASE)

# Obvious REQUEST signals. If any fire, we ESCALATE straight away (skip stage 2).
# These are intentionally broad - a false "looks like a request" only costs a
# AI call, which is the safe direction.
_REQUEST_SIGNALS = re.compile(
    r"\b("
    r"can you|could you|could we|can we|would you|will you|"
    r"please (add|update|change|fix|send|share|create|build|include|remove|redo|revise)|"
    r"pls|plz|"
    r"add|include|create|build|"
    r"make (a|an|the|it|this|our|my)\b|"
    r"change (the|this|that|our|my)\b|modify (the|this|that|our|my)\b|"
    r"update (the|this|that|our|my)\b|adjust (the|this|that|our|my)\b|"
    r"please update|can you update|could you update|"
    r"any update on|status of|where are we with|"
    r"redo|rework|revise|revision|another (round|version|pass)|one more|"
    r"also (need|want|add|do)|while you'?re at it|on top of|in addition|"
    r"instead|swap|replace|remove|delete|"
    r"new (page|section|feature|screen|flow|version|variant)|"
    r"how about|what if|is it possible|any (chance|way)|"
    r"i (need|want|'d like|would like)|we (need|want|'d like|would like)|"
    r"let'?s (add|do|change|include)|"
    r"is .{0,50} (done|ready|finished|designed|complete|working|started)\b|"
    r"did you finish|has .{0,40} been (done|started|finished)|"
    r"what about .{0,50}\?"
    r")\b",
    re.IGNORECASE,
)


def _looks_request_shaped(text: str) -> bool:
    """Broad check: does this smell like a request? Biased to True (safe)."""
    if _REQUEST_SIGNALS.search(text):
        return True
    # Bare "please" / "pls" at end often means a real ask ("pls ?").
    if re.search(r"\b(pls|plz)\s*\??\s*$", text, re.I):
        return True
    return False


def stage1(text: str) -> Optional[GateResult]:
    """
    Returns a GateResult if Stage 1 is confident, else None (fall through to Stage 2).
      - Confident non-request  -> SKIP
      - Confident request      -> ESCALATE
      - Unsure                 -> None
    """
    stripped = text.strip()

    if not stripped:
        return GateResult(GateDecision.SKIP, "stage1_nonrequest", "empty after extraction")

    if _EMOJI_OR_PUNCT_ONLY.match(stripped) or _SLACK_EMOJI_ONLY.match(stripped):
        return GateResult(GateDecision.SKIP, "stage1_nonrequest", "emoji/punctuation only")

    # Request signal beats ack: "thanks, can you also add X" must escalate.
    if _looks_request_shaped(stripped):
        return GateResult(GateDecision.ESCALATE, "stage1_request", "request signal present")

    if _ACK_ONLY.match(stripped) or _ACK_PHRASE.match(stripped):
        return GateResult(GateDecision.SKIP, "stage1_nonrequest", "acknowledgment only")

    if _CHATTER_STATUS.match(stripped):
        return GateResult(GateDecision.SKIP, "stage1_nonrequest", "check-in or admin chatter")

    # Very short and no request signal - unlikely to be a work request, but let
    # Stage 2 (or escalation) decide rather than hard-skipping here, because short
    # loaded asks exist ("dark mode too"). We only hard-skip the ack/emoji cases.
    return None


# ---------------------------------------------------------------------------
# Embedding backend (local sentence-transformers, lazy singleton)
# ---------------------------------------------------------------------------

class _Embedder:
    """
    Lazy singleton around sentence-transformers. If the model can't load, stays
    disabled and the gate falls back to escalate-on-stage1-miss.
    """
    _instance: Optional["_Embedder"] = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = None
        self.enabled = False
        try:
            from sentence_transformers import SentenceTransformer  # local, ~80MB
            self.model = SentenceTransformer(model_name)
            self.enabled = True
            logger.info("embedding_gate: loaded %s", model_name)
        except Exception as e:  # noqa: BLE001 - any failure => disabled, safe
            logger.warning("embedding_gate: model unavailable, stage 2 disabled (%s)", e)

    @classmethod
    def get(cls) -> "_Embedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, texts: Sequence[str]):
        """Return L2-normalized vectors so dot product == cosine similarity."""
        # normalize_embeddings=True => cosine via plain dot product later
        return self.model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )


# ---------------------------------------------------------------------------
# Reference clusters
# ---------------------------------------------------------------------------
# The SKIP signal is proximity to the NON-REQUEST cluster, NOT to deliverables.
# We embed deliverables (and known creep, if provided) only to compute a MARGIN:
# we skip only when the message is clearly closer to chatter than to any work
# topic. Deliverable proximity never by itself causes a skip.

# Generic, project-independent "this is not a work request" exemplars.
# Kept broad and mundane on purpose.
NON_REQUEST_EXEMPLARS = [
    # Thanks & acks
    "thanks so much for this",
    "thank you really appreciate it",
    "cheers mate that looks great",
    "perfect love it",
    "looks good to me",
    "sounds good",
    "ok got it",
    "great work on this so far",
    "nice one well done",
    "no worries take your time",
    "really happy with the result",
    "that's exactly what we wanted",
    "appreciate the quick turnaround",
    "you're the best",
    "lgtm",
    # Check-ins & timing (not scope asks)
    "just checking in on progress",
    "how is it going",
    "how's everything going on your end",
    "when do you think the next update will be ready",
    "any news on timing",
    "ping me when you have something to show",
    "looking forward to seeing it",
    "let me know if you need anything from me",
    # Social / admin
    "good morning hope you had a good weekend",
    "good morning team",
    "hi everyone",
    "welcome to the channel",
    "congrats on the launch",
    "i'll be ooo thursday and friday",
    "out sick today back tomorrow",
    "on a call will reply later",
    "traveling this week slower to respond",
    "sorry for the delayed reply",
    # Project coordination (not new work)
    "following up on my last message",
    "bumping this thread",
    "sent you the brand assets via email",
    "did you get the files i uploaded yesterday",
    "shared in the figma link above",
    "left comments on the mockup",
    "approved the latest version in email",
    "invoice received thanks",
    "payment sent via razorpay",
    "signed the sow copy you sent",
    "budget approval came through from finance",
    "legal signed off on the contract",
    "demo went really well yesterday",
    "client loved the preview in our standup",
    "showed it to the founder big thumbs up",
    "we're presenting this to investors friday",
    "standup update client is happy with direction",
    "quick note board meeting went well",
    "looping in sarah from our side",
    "forwarding this to our marketing lead",
    # Compliments without asks
    "the team is really happy so far",
    "excited to see the next version",
    "no rush on this one we're not in a hurry",
    "back on monday if you need me",
    "did you get the files i uploaded yesterday",
    "our ceo saw the wip and was impressed",
    "budget approval came through from finance",
    "legal signed off on the contract",
    "just wanted to say great work on this so far",
    "really appreciate how responsive you've been",
    "catching up on messages now",
    "hope the holidays were good",
    "any thoughts when you get a chance",
    "reviewed the staging site on my phone",
]
class ReferenceVectors:
    """Cached per project. Rebuild on brief setup / update."""
    non_request: "object" = None   # np.ndarray [N, D]
    deliverables: "object" = None  # np.ndarray [M, D] or None
    known_creep: "object" = None   # np.ndarray [K, D] or None
    ready: bool = False


def build_reference_vectors(
    deliverable_texts: Sequence[str],
    known_creep_texts: Optional[Sequence[str]] = None,
) -> ReferenceVectors:
    """
    Build and cache the reference vectors for one project.
    Call this on brief setup and on brief/CO update. Cheap; do it off the hot path.
    """
    emb = _Embedder.get()
    if not emb.enabled:
        return ReferenceVectors(ready=False)

    refs = ReferenceVectors()
    refs.non_request = emb.embed(NON_REQUEST_EXEMPLARS)
    if deliverable_texts:
        refs.deliverables = emb.embed(list(deliverable_texts))
    if known_creep_texts:
        refs.known_creep = emb.embed(list(known_creep_texts))
    refs.ready = True
    return refs


# ---------------------------------------------------------------------------
# Stage 2 - embedding novelty router
# ---------------------------------------------------------------------------

def _max_sim(vec, matrix) -> float:
    """Max cosine similarity between one normalized vec and a normalized matrix."""
    if matrix is None or len(matrix) == 0:
        return 0.0
    # vec: [D], matrix: [N, D], both L2-normalized => dot == cosine
    import numpy as np
    sims = matrix @ vec
    return float(np.max(sims))


def _top_k_mean_sim(vec, matrix, k: int = 3) -> float:
    """Mean of top-k cosine similarities - smoother than max-only."""
    if matrix is None or len(matrix) == 0:
        return 0.0
    import numpy as np
    sims = matrix @ vec
    k = min(k, len(sims))
    top = np.partition(sims, -k)[-k:]
    return float(np.mean(top))


def stage2(text: str, refs: ReferenceVectors, cfg: GateConfig) -> GateResult:
    """
    Only reached when Stage 1 was unsure. Decide SKIP vs ESCALATE using proximity
    to the non-request cluster, with a margin over work clusters and a novelty floor.
    Fails open to ESCALATE on any uncertainty or error.
    """
    emb = _Embedder.get()
    if not emb.enabled or not refs.ready or refs.non_request is None:
        return GateResult(GateDecision.ESCALATE, "fallback_escalate",
                          "embeddings unavailable")

    if len(text.split()) < cfg.min_words_for_stage2:
        # Short and survived stage 1 (no ack match, no request signal). Could be a
        # loaded micro-ask ("dark mode too" already caught by signals; this is the
        # residue). Cheap to let AI look.
        return GateResult(GateDecision.ESCALATE, "stage2_escalate", "too short to skip safely")

    try:
        v = emb.embed([text])[0]
        sim_nonreq = _top_k_mean_sim(v, refs.non_request, cfg.nonrequest_top_k)
        sim_deliv = _max_sim(v, refs.deliverables)
        sim_creep = _max_sim(v, refs.known_creep)
        sim_work = max(sim_deliv, sim_creep)
    except Exception as e:  # noqa: BLE001
        logger.warning("embedding_gate stage2 error, escalating: %s", e)
        return GateResult(GateDecision.ESCALATE, "fallback_escalate", f"stage2 error: {e}")

    # Novelty: far from everything we know → unusual → let AI judge.
    if max(sim_nonreq, sim_work) < cfg.novelty_floor:
        return GateResult(GateDecision.ESCALATE, "stage2_escalate",
                          f"novel (nonreq={sim_nonreq:.2f}, work={sim_work:.2f})",
                          similarity=sim_nonreq)

    # SKIP only if clearly chatter AND clearly closer to chatter than to any work.
    clearly_chatter = sim_nonreq >= cfg.skip_nonrequest_sim
    clear_margin = (sim_nonreq - sim_work) >= cfg.skip_margin
    if clearly_chatter and clear_margin:
        return GateResult(GateDecision.SKIP, "stage2_skip",
                          f"chatter (nonreq={sim_nonreq:.2f} > work={sim_work:.2f})",
                          similarity=sim_nonreq)

    # Anything else - including "somewhat close to a deliverable" - escalates.
    return GateResult(GateDecision.ESCALATE, "stage2_escalate",
                      f"not confidently chatter (nonreq={sim_nonreq:.2f}, work={sim_work:.2f})",
                      similarity=sim_nonreq)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def gate_message(
    text: str,
    refs: Optional[ReferenceVectors] = None,
    cfg: Optional[GateConfig] = None,
) -> GateResult:
    """
    Decide SKIP vs ESCALATE for one already-extracted, already-prefiltered message.

    Call this AFTER your existing prefilter (bots/edits/joins/self already removed)
    and AFTER extract_message_text(). On ESCALATE, run your existing classify().
    On SKIP, do nothing.

    `refs` is the per-project ReferenceVectors from build_reference_vectors().
    If refs is None or not ready, Stage 2 is skipped and stage-1-unsure => ESCALATE
    (safe: we just spend more AI calls, never miss creep).
    """
    cfg = cfg or GateConfig()

    s1 = stage1(text)
    if s1 is not None:
        return s1

    if refs is None or not refs.ready:
        return GateResult(GateDecision.ESCALATE, "fallback_escalate",
                          "no reference vectors; escalating by default")

    return stage2(text, refs, cfg)
