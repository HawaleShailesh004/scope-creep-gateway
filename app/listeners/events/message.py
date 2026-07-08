import asyncio
import json
import logging
import os
from logging import Logger

from slack_bolt.context.async_context import AsyncBoltContext
from slack_bolt.context.say.async_say import AsyncSay
from slack_sdk.web.async_client import AsyncWebClient

from classifier import classify
from services.absorbed import log_absorbed
from services.classifier_router import route_classification
from services.clients import resolve_client
from services.embedding_cache import ensure_embedding_refs
from services.embedding_gate import GateDecision, gate_message
from services.message_text import extract_message_text
from services.mockup_classifier import classify_mockup_from_event, pick_classifiable_file
from services.prefilter import is_project_channel_message, should_skip_message
from services.project_context import load_project_by_channel
from services.projects import is_analysis_allowed
from services.scope_warnings import send_scope_warning
from services.user_messages import CLASSIFIER_CHECK_FAILED

logger = logging.getLogger(__name__)


async def handle_message(
    client: AsyncWebClient,
    context: AsyncBoltContext,
    event: dict,
    logger: Logger,
    say: AsyncSay,
):
    """Classify client messages in project channels; warn freelancer on flags."""
    if not is_project_channel_message(event):
        logger.debug("scope_classifier_skip not_a_project_channel event=%s", event)
        return

    if should_skip_message(event):
        logger.debug("scope_classifier_skip prefilter event=%s", event)
        return

    channel_id = event.get("channel")
    user_id = event.get("user")
    text = extract_message_text(event)

    project_context = None
    try:
        project_context = await asyncio.to_thread(
            load_project_by_channel, channel_id
        )
        if not project_context:
            logger.info("scope_classifier_skip no_project channel=%s", channel_id)
            return

        project = project_context["project"]
        if not is_analysis_allowed(project):
            logger.info(
                "scope_classifier_skip disclosure_or_disabled project=%s "
                "disclosure_ts=%s classification_enabled=%s",
                project.get("project_name"),
                project.get("disclosure_ts"),
                project.get("classification_enabled"),
            )
            return

        if user_id == project.get("freelancer_slack_id"):
            logger.info(
                "scope_classifier_skip freelancer user=%s project=%s",
                user_id,
                project.get("project_name"),
            )
            return
        if user_id != project.get("client_slack_id"):
            logger.info(
                "scope_classifier_skip not_client user=%s expected_client=%s",
                user_id,
                project.get("client_slack_id"),
            )
            return

        deliverables = project_context["deliverables"]

        client_id = await asyncio.to_thread(
            resolve_client,
            freelancer_slack_id=project["freelancer_slack_id"],
            client_slack_id=project["client_slack_id"],
        )

        result = None
        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        if pick_classifiable_file(event) and bot_token:
            result = await classify_mockup_from_event(
                bot_token,
                event,
                brief_markdown=project_context["brief_markdown"],
                deliverables=deliverables,
            )

        if result is None:
            refs = await asyncio.to_thread(
                ensure_embedding_refs, project["id"], deliverables
            )
            gate = await asyncio.to_thread(gate_message, text or "", refs)
            logger.info(
                "embedding_gate %s",
                json.dumps(
                    {
                        "decision": gate.decision.value,
                        "stage": gate.stage,
                        "reason": gate.reason,
                        "similarity": gate.similarity,
                    },
                    ensure_ascii=False,
                ),
            )
            if gate.decision == GateDecision.SKIP:
                return

            result = await asyncio.to_thread(
                classify,
                project_context["brief_markdown"],
                deliverables,
                text or "See attached mockup/design file.",
                project_context.get("exclusions") or [],
            )

        decision = route_classification(
            classification=result,
            project_id=project["id"],
            deliverables=project_context.get("deliverable_rows", []),
        )

        log_payload = {
            "channel_id": channel_id,
            "project": project.get("project_name"),
            "message": text[:200],
            "classification": result,
            "route": decision.action,
        }
        logger.info("scope_classifier %s", json.dumps(log_payload, ensure_ascii=False))

        if decision.action == "auto_absorb":
            await asyncio.to_thread(
                log_absorbed,
                project_id=project["id"],
                client_id=client_id,
                trigger_message_ts=event.get("ts", ""),
                trigger_text=text,
                task_summary=result.get("new_task_summary"),
                estimated_value=float(result.get("estimated_value") or 0),
                estimated_hours=float(result.get("estimated_hours") or 0) or None,
                size=result.get("size"),
                source="auto",
            )
            return

        if decision.action == "revision_warn":
            deliverable = decision.deliverable or {}
            await send_scope_warning(
                client,
                channel_id=channel_id,
                freelancer_id=project["freelancer_slack_id"],
                message_ts=event.get("ts", ""),
                message_text=text,
                project=project,
                classification=result,
                client_id=client_id,
                revision_deliverable=deliverable.get("description"),
                revision_limit=deliverable.get("revision_limit"),
            )
            return

        if decision.action == "warn":
            await send_scope_warning(
                client,
                channel_id=channel_id,
                freelancer_id=project["freelancer_slack_id"],
                message_ts=event.get("ts", ""),
                message_text=text,
                project=project,
                classification=result,
                client_id=client_id,
            )

    except Exception as exc:
        logger.exception("Failed to classify client message: %s", exc)
        if project_context:
            project = project_context["project"]
            freelancer_id = project.get("freelancer_slack_id")
            if freelancer_id and channel_id:
                try:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=freelancer_id,
                        text=CLASSIFIER_CHECK_FAILED,
                    )
                except Exception:
                    logger.exception("Failed to notify freelancer of classifier error")
