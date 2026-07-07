"""User-facing copy - keep friendly, polite, and professional."""

# --- Project brief / setup ---

BRIEF_ALREADY_EXISTS = (
    "This channel already has a project brief.\n\n"
    "• Open the *Canvas* tab to view the current scope and Scope Health.\n"
    "• To bill for new work, run `/change-order` or use *Flag as scope change* on a client message.\n"
    "• To edit deliverables or budget, run `/update-brief`."
)

SETUP_IN_PROGRESS = (
    "We're already setting up the project brief for this channel. "
    "Please give it a moment - you'll see a confirmation here when it's ready."
)

SETUP_LAUNCHER_INTRO = (
    "Ready to define the project scope? "
    "Choose how you'd like to set up the brief — only you can see this."
)

SETUP_PATH_PROMPT = (
    "Want to set up scope? I can draft it from your conversation, "
    "or you can fill it in yourself."
)

SETUP_PATH_EXTRACT = "Draft from conversation"

SETUP_PATH_MANUAL = "Fill it in myself"

EXTRACT_READY = (
    "Here's what I picked up from your chat — check it, tweak anything, "
    "and confirm. I won't lock anything in without you."
)

EXTRACT_IN_PROGRESS = (
    ":hourglass_flowing_sand: Reading your kickoff chat and drafting a brief…"
)

EXTRACT_FAILED = (
    "I couldn't draft a brief from the conversation. "
    "Click *Fill it in myself* below, or post a few kickoff messages first."
)

EXTRACT_DRAFT_READY = (
    ":white_check_mark: Draft ready from your conversation — "
    "click *Review AI draft* to check, tweak, and confirm.\n"
    "_You'll still need to pick the client in the form._"
)

EXTRACT_PARTIAL = (
    ":pencil2: I pulled some of this from your chat, but it's not enough to lock in yet.\n"
    "Still needed: *{missing}*\n"
    "Click *Review AI draft* to complete the form, or *Fill it in myself*."
)

EXTRACT_MODAL_EMPTY = (
    ":memo: *No kickoff messages yet* — fill in the required fields below."
)

EXTRACT_MODAL_INSUFFICIENT = (
    ":warning: *Fill required fields* — your chat didn't clarify scope enough. "
    "Still needed: *{missing}*"
)

EXTRACT_MODAL_PARTIAL = (
    ":pencil2: *Some fields pre-filled from chat.* Still required: *{missing}*"
)

EXTRACT_MODAL_STILL_NEED_CLIENT = (
    ":white_check_mark: *Draft from your chat is loaded.* "
    "Pick the *client* below, then click *Create brief*."
)

EXTRACT_MODAL_FAILED = (
    ":warning: *Couldn't read your chat* — please fill the required fields below."
)

EXTRACT_EMPTY_OPENED = (
    ":memo: No kickoff messages in this channel yet — "
    "opened the blank brief form for you."
)

EXTRACT_DRAFT_EXPIRED = (
    "That draft expired. Run `/setup-brief` again, or click *Fill it in myself*."
)

SETUP_OPENING_FORM = ":hourglass_flowing_sand: Opening the project brief form…"

SETUP_FORM_READY = (
    ":white_check_mark: The project brief form is open above — "
    "fill it in and click *Create brief* when you're done."
)

SETUP_SUCCESS_EPHEMERAL = (
    ":white_check_mark: Project brief created for *{project_name}*. "
    "Scope Health: 100%. Check the Canvas tab for the full scope."
)

SETUP_CREATING = (
    "Thanks! We're creating your project brief and canvas now - "
    "this usually takes about few seconds."
)

SETUP_FAILED = (
    "We weren't able to complete the project brief setup. "
    "Please try `/setup-brief` again. If the issue persists, check that the bot is online."
)

SETUP_SUCCESS_CHANNEL = (
    "Project brief created for *{project_name}*. "
    "Scope Health: 100%. The canvas is attached to this channel.\n"
    ":shield: Scope Creep Gateway is watching this project for the freelancer. "
    "Detections are private to them."
)

SETUP_SUCCESS_NOT_IN_CHANNEL = (
    "Project brief saved for *{project_name}* and the canvas was created. "
    "Invite me to this channel with `/invite @Scope Creep Gateway` "
    "if you'd like public confirmation messages here."
)

# --- Change orders ---

CHANGE_ORDER_LAUNCHER_INTRO = (
    "Need to capture additional work? "
    "Click below to draft a change order. Only you can see this message."
)

CHANGE_ORDER_IN_PROGRESS = (
    "A change order is already being prepared. "
    "Please wait a moment for the form to open."
)

CHANGE_ORDER_OPENING_FORM = ":hourglass_flowing_sand: Opening the change order form…"

CHANGE_ORDER_FORM_READY = (
    ":white_check_mark: The change order form is open above — "
    "review the draft and click *Post to channel* when ready."
)

CHANGE_ORDER_POSTING = (
    ":hourglass_flowing_sand: Posting your change order and updating the scope canvas — "
    "just a moment."
)

CHANGE_ORDER_POSTED_SUCCESS = (
    ":white_check_mark: Change Order #{order_number} posted. "
    "Scope Health is now *{scope_health}%*."
)

CANVAS_UPDATE_FAILED = (
    "Your change order was posted, but we couldn't refresh the Canvas tab. "
    "Scope Health in the database is *{scope_health}%* — try reopening the canvas."
)

CHANGE_ORDER_ALREADY_POSTED = (
    "This change order has already been posted to the channel."
)

CHANGE_ORDER_NO_LONGER_AVAILABLE = (
    "This change order is no longer available to post. "
    "It may have been dismissed or already submitted."
)

CHANGE_ORDER_ALREADY_PROCESSING = (
    "This change order is already being posted. Please wait a moment."
)

CHANGE_ORDER_CANNOT_PAY = (
    "This change order can't be marked as paid right now. "
    "It may still be a draft or already completed."
)

CHANGE_ORDER_FORM_OPENING = (
    "The change order form is already opening. Please wait a moment."
)

CHANGE_ORDER_FLAG_IN_PROGRESS = (
    "A change order is already being prepared. "
    "Please wait before flagging another message."
)

# --- Modals (change order errors) ---

CO_ERROR_NOT_FOUND = (
    "We couldn't find that change order. "
    "Please start again from the scope warning or `/change-order`."
)

CO_ERROR_DISMISSED = (
    "This flag was dismissed as not scope creep. "
    "Post a new client message if scope changes again."
)

CO_ERROR_ALREADY_POSTED = (
    "A change order has already been created for this flag."
)

CO_ERROR_NO_PROJECT = (
    "This channel doesn't have a project brief yet. "
    "Run `/setup-brief` first to define the scope."
)

CO_ERROR_FREELANCER_ONLY = (
    "Only the freelancer on this project can create change orders."
)

CO_ERROR_NO_MESSAGE_TEXT = (
    "That message doesn't contain any text to flag. "
    "Please choose a message with a clear request."
)

CO_ERROR_FLAG_EXISTS = (
    "A scope flag already exists for this message. "
    "Use *Generate Change Order* on the existing warning."
)

CO_ERROR_BOOTSTRAP_BUSY = (
    "A change order is already being prepared. Please wait a moment."
)

CO_ERROR_PREPARE_FAILED = (
    "We couldn't prepare the change order: {detail}. Please try again."
)

CO_ERROR_DRAFT_FAILED = (
    "We couldn't draft the change order: {detail}. Please try again."
)

# --- Scope warnings ---

SCOPE_WARNING_TITLE = "Possible scope creep detected"

SCOPE_WARNING_BODY_INTRO = 'Client asked: "{quoted}"'

SCOPE_WARNING_NOT_IN_BRIEF = "This isn't in the agreed brief."

SCOPE_WARNING_PRIOR_MENTION = (
    ":warning: This was also raised on {prior_mention_date} and not added to scope."
)

DISMISS_SUCCESS = "Dismissed - marked as not scope creep."

DISMISS_FAILED = (
    "We couldn't dismiss that warning. Please try again or use "
    "*Flag as scope change* on the message if needed."
)

CLASSIFIER_CHECK_FAILED = (
    "We couldn't check that client message against the brief just now. "
    "If it looked like new scope, use *Flag as scope change* on the message."
)

SETUP_CLIENT_CANNOT_BE_FREELANCER = (
    "The client and freelancer must be different people. "
    "Please select your client's Slack account."
)

SETUP_FREELANCER_ONLY_HINT = (
    "Tip: The freelancer on the project should run `/setup-brief` "
    "so scope warnings reach the right person."
)

SIMULATE_PAYMENT_FREELANCER_ONLY = (
    "Only the freelancer can mark a change order as paid in demo mode."
)

LEGACY_WARNING_BUTTON = (
    "This warning was created before a recent update. "
    "Please ask the client to send a new message, then use the fresh warning."
)

# --- Triggers / timeouts ---

TRIGGER_EXPIRED = (
    "That action timed out - the connection may have been briefly interrupted. "
    "Please try again."
)

TRIGGER_EXPIRED_SETUP = (
    "The setup command timed out before the form could open. "
    "Please run `/setup-brief` again and click the button when it appears."
)

TRIGGER_EXPIRED_FORM_BUTTON = (
    "We couldn't open the form. Please click the button again."
)

TRIGGER_EXPIRED_SCOPE_FLAG = (
    "That shortcut timed out. Right-click the message and choose "
    "*Flag as scope change* again."
)

TRIGGER_EXPIRED_CHANGE_ORDER = (
    "That action timed out. Please trigger a fresh scope warning and try again."
)

# --- Generic ---

POST_CHANGE_ORDER_FAILED = (
    "We couldn't post the change order. Please try again or run `/change-order`."
)

# --- Tier 1: disclosure & trust ---

DISCLOSURE_NOTICE = (
    ":shield: *Scope Creep Gateway is active in this channel.* "
    "It helps {freelancer} keep the agreed scope and budget clear by tracking "
    "messages against the project brief. Detections are private to {freelancer}, "
    "nothing is shared outside this channel, and messages are never used to train AI. "
    "You can ask {freelancer} to remove it anytime."
)

BOT_JOIN_INTRO = (
    "Hi! I'm Scope Creep Gateway. Run `/setup-brief` or `/import-brief` when you're "
    "ready to define the project scope."
)

IMPORT_BRIEF_LAUNCHER_INTRO = (
    "Import a scope document into the setup form, or open the form manually."
)

IMPORT_BRIEF_NO_FILE = (
    "That message doesn't include a scope document I can read. "
    "Attach a PNG, JPG, PDF, or similar and try again."
)

IMPORT_BRIEF_FAILED = (
    "I couldn't read that document. Try `/setup-brief` and enter the scope manually."
)

GATEWAY_DISABLED = (
    "Scope classification is paused in this channel. "
    "Run `/scope-gateway-on` to resume."
)

GATEWAY_ENABLED = (
    "Scope classification is active again in this channel."
)

GATEWAY_TOGGLE_FREELANCER_ONLY = (
    "Only the freelancer on this project can turn the gateway on or off."
)

# --- Tier 1: absorb ---

ABSORB_CONFIRMED = (
    "Logged as goodwill — I'll keep track of what you've absorbed."
)

ABSORB_THRESHOLD_NUDGE = (
    "_You've absorbed {total} from this client already — consider billing this one._"
)

CAPACITY_NUDGE = (
    "_Heads-up — that's about {hours}h of unbilled extras this week already. Still your call._"
)

WEEKLY_ABSORBED_LINE = (
    "🕐 Absorbed this week: {hours}h (~{value}) across {clients} clients. Heaviest: {top_client}."
)

WEEKLY_BILLING_LINE = (
    "💸 This week: {billed} billed · {approved} approved · {pending} awaiting client."
)

CANVAS_APPROVED_LINE = "**Approved additions:** {value}"

SCOPE_EXCLUSION_CITATION = (
    "_This matches something noted as out of scope at kickoff._"
)

ABSORBED_SUMMARY_EMPTY = (
    "No absorbed work logged yet for this project."
)

ABSORBED_SUMMARY = (
    "*Absorbed work for this project*\n"
    "• Manual (Let it slide): {manual_count} items\n"
    "• Auto (small asks): {auto_count} items\n"
    "• Estimated value absorbed: {total_value}"
)

# --- Tier 1: client intelligence ---

CLIENT_PATTERN_NUDGE = (
    "_This is the {nth} out-of-scope ask from {client} this month._"
)

CLIENT_REPORT_EMPTY = (
    "No client stats yet. Set up a project brief with a client first."
)

CLIENT_REPORT = (
    "*Client report — {client}*\n"
    "• Projects: {project_count}\n"
    "• Open flags: {open_flags}\n"
    "• Absorbed: {absorbed_count} items ({absorbed_value}, ~{absorbed_hours}h)\n"
    "• Billed change orders: {billed_count}\n"
    "• Approved: {approved_value} · Pending: {pending_value}\n"
    "• Out-of-scope asks this month: {monthly_asks}"
)

STUDIO_WEEKLY_SUMMARY = (
    "📋 *Your scope week — {studio_name}*\n\n"
    "Across {active_projects} active projects:\n"
    "🕐 Absorbed: ~{absorbed_hours}h (~{absorbed_value}) unbilled extras — heaviest: {top_client}\n"
    "{billing_line}\n"
    "{heaviest_line}\n"
    "{clean_line}\n"
    "{worth_line}"
)

STUDIO_REPORT_LAUNCHER = (
    "Your studio-level scope summary — capacity, billing, and client patterns. "
    "Click below. Only you can see this."
)

CLIENT_REPORT_LAUNCHER = (
    "See how this client compares across projects. "
    "Click below — only you can see this."
)

# --- Tier 1: revisions ---

SCOPE_WARNING_REVISION = (
    "This looks like a revision request on *{deliverable}*, "
    "and you've hit the agreed revision limit ({limit} rounds)."
)

SCOPE_WARNING_REVISION_BODY = (
    'Client asked: "{quoted}"\n'
    "This is a revision on *{deliverable}* — not new scope, but over the agreed limit."
)

# --- Tier 2: draft reply ---

DRAFT_REPLY_FAILED = (
    "We couldn't draft a reply just now. Please try again in a moment."
)

DRAFT_REPLY_EMPTY = "Add a message before posting."

DRAFT_REPLY_FREELANCER_ONLY = "Only the freelancer on this project can post this reply."

DRAFT_REPLY_POST_FAILED = (
    "We couldn't post your reply to the channel. Please try again or paste it manually."
)

# --- Tier 2: update brief ---

UPDATE_BRIEF_LAUNCHER_INTRO = (
    "Edit deliverables, budget, or deadline for this project. "
    "Change-order items stay in scope automatically."
)

UPDATE_BRIEF_NO_PROJECT = (
    "This channel doesn't have a project brief yet. Run `/setup-brief` first."
)

UPDATE_BRIEF_FREELANCER_ONLY = (
    "Only the freelancer on this project can update the brief."
)

UPDATE_BRIEF_SUCCESS = (
    ":white_check_mark: Project brief updated. The canvas has been refreshed."
)

UPDATE_BRIEF_FAILED = (
    "We couldn't update the project brief. Please try again."
)

UPDATE_BRIEF_SAVING = (
    ":hourglass_flowing_sand: Updating your project brief and refreshing the canvas…"
)

APP_HOME_PRIVACY = (
    "*Privacy & control*\n"
    "• *What I can see:* messages in channels where I'm added, to check them against "
    "the project brief.\n"
    "• *What I store:* only the details of flagged scope changes — not your everyday "
    "messages.\n"
    "• *What I never do:* share or sell your data, or use it to train AI.\n"
    "• *Turn me off:* remove me from a channel, or run `/scope-gateway-off` there."
)
