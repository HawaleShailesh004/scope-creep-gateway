from __future__ import annotations

import json
import os

from services.brief_template import format_budget


def _card_value(
    *,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
) -> str:
    return json.dumps(
        {
            "co_id": change_order_id,
            "ch": channel_id,
            "msg_ts": message_ts,
            "thread_ts": thread_ts,
        }
    )


def is_demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "true").strip().lower() in ("1", "true", "yes")


def build_change_order_card_blocks(
    *,
    order_number: int,
    title: str,
    task_description: str,
    estimated_cost: float,
    timeline_impact_days: int,
    budget_total: float | None,
    currency: str,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
    project_id: str,
    paid: bool = False,
    include_payment: bool = False,
    include_draft_reply: bool = False,
) -> list[dict]:
    """Channel-visible CO card.

    Payment buttons are client-only (ephemeral) — keep include_payment=False on
    the public post. Draft reply is freelancer-only (ephemeral).
    """
    new_total = None
    if budget_total is not None:
        new_total = float(budget_total) + estimated_cost

    lines = [
        f":page_facing_up: *Change Order #{order_number} - {title}*",
        "",
        task_description,
        "",
        f"• Additional cost:   {format_budget(estimated_cost, currency)}",
        f"• Timeline impact:   +{timeline_impact_days} days",
    ]
    if new_total is not None:
        lines.append(f"• New total:         {format_budget(new_total, currency)}")

    if paid:
        lines.extend(["", ":white_check_mark: *Paid* - thank you!"])
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]

    if not include_payment and not include_draft_reply:
        lines.extend(
            [
                "",
                "_Awaiting client approval._",
            ]
        )

    blocks: list[dict] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
    ]

    button_value = _card_value(
        change_order_id=change_order_id,
        channel_id=channel_id,
        message_ts=message_ts,
        thread_ts=thread_ts,
    )

    if include_payment:
        payment_url = os.environ.get(
            "STRIPE_PAYMENT_LINK_URL",
            "https://buy.stripe.com/test_placeholder",
        )
        blocks.append(
            {
                "type": "actions",
                "block_id": f"change_order_{change_order_id}",
                "elements": _payment_actions(
                    payment_url=payment_url,
                    button_value=button_value,
                ),
            }
        )

    if include_draft_reply:
        blocks.append(
            {
                "type": "actions",
                "block_id": f"change_order_draft_{change_order_id}",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "draft_reply",
                        "text": {"type": "plain_text", "text": "Draft the reply"},
                        "value": json.dumps(
                            {
                                "co_id": change_order_id,
                                "ch": channel_id,
                                "pid": project_id,
                                "ts": thread_ts or message_ts,
                            }
                        ),
                    }
                ],
            }
        )

    return blocks


def build_client_payment_ephemeral_blocks(
    *,
    order_number: int,
    title: str,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
) -> list[dict]:
    """Only visible to the client — Approve & Pay (+ Simulate in demo)."""
    payment_url = os.environ.get(
        "STRIPE_PAYMENT_LINK_URL",
        "https://buy.stripe.com/test_placeholder",
    )
    button_value = _card_value(
        change_order_id=change_order_id,
        channel_id=channel_id,
        message_ts=message_ts,
        thread_ts=thread_ts,
    )
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Change Order #{order_number} — {title}*\n"
                    "Only you see these payment options."
                ),
            },
        },
        {
            "type": "actions",
            "block_id": f"change_order_pay_{change_order_id}",
            "elements": _payment_actions(
                payment_url=payment_url,
                button_value=button_value,
            ),
        },
    ]


def build_freelancer_draft_ephemeral_blocks(
    *,
    order_number: int,
    change_order_id: str,
    channel_id: str,
    project_id: str,
    thread_ts: str,
) -> list[dict]:
    """Only visible to the freelancer — draft a client-facing reply."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Change Order #{order_number} is in the thread. "
                    "Payment options were sent privately to the client."
                ),
            },
        },
        {
            "type": "actions",
            "block_id": f"change_order_draft_{change_order_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "draft_reply",
                    "text": {"type": "plain_text", "text": "Draft the reply"},
                    "value": json.dumps(
                        {
                            "co_id": change_order_id,
                            "ch": channel_id,
                            "pid": project_id,
                            "ts": thread_ts,
                        }
                    ),
                }
            ],
        },
    ]


def _payment_actions(*, payment_url: str, button_value: str) -> list[dict]:
    elements = [
        {
            "type": "button",
            "action_id": "approve_pay_link",
            "text": {"type": "plain_text", "text": "Approve & Pay"},
            "style": "primary",
            "url": payment_url,
        },
    ]
    if is_demo_mode():
        elements.append(
            {
                "type": "button",
                "action_id": "simulate_payment",
                "text": {"type": "plain_text", "text": "Simulate payment"},
                "value": button_value,
            }
        )
    return elements
