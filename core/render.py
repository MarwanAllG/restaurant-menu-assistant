from __future__ import annotations

import re

from core.menu import Menu, contains
from core.schemas import AssistantResponse, Constraints

ALLERGEN_QUALIFICATION = "Filtered using listed allergens"


def escape(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", str(text))


def constraint_text(c: Constraints) -> str:
    bits = []
    for key, value in c.model_dump().items():
        if value is None or value is False or value == []:
            continue
        label = key.replace("_", " ")
        bits.append(f"{label}: {escape(', '.join(value) if isinstance(value, list) else value)}")
    return "; ".join(bits) or "none"


def render(
    selection: AssistantResponse, menu: Menu, active: Constraints, profile: list[dict]
) -> str:
    lines = [selection.reply]
    for item_id in selection.item_ids:
        item = menu.by_id[item_id]
        reasons = []
        for p in profile:
            if (
                p["dimension"] == "cuisine"
                and p["value"] == "like"
                and p["subject"] == item.cuisine.casefold()
            ):
                reasons.append(f"Matches your preference for {item.cuisine} cuisine")
            if p["dimension"] == "ingredient" and p["value"] == "like":
                matched = [i for i in item.ingredients if contains(p["subject"], i)]
                if matched:
                    reasons.append("Includes " + matched[0])
        if active.max_price is not None:
            reasons.append(f"Within your {active.max_price:g} SAR per-item budget")
        if active.vegetarian is True:
            reasons.append("Classified vegetarian in the demo menu")
        if active.vegan is True:
            reasons.append("Classified vegan in the demo menu")
        if active.max_spice is not None:
            reasons.append(f"Spice {item.spiceLevel}/3 meets your maximum of {active.max_spice}")
        dietary = ", ".join(
            f"{key}: {'unknown' if val is None else 'yes' if val else 'no'}"
            for key, val in item.dietary.model_dump().items()
        )
        lines.append(
            f"### {escape(item.name)} · {item.price:g} {item.currency}\n"
            f"{escape(item.category)} · {escape(item.cuisine)} · Spice {item.spiceLevel}/3\n\n"
            f"![{escape(item.name)}]({item.image})\n\n"
            f"**Ingredients:** {escape(', '.join(item.ingredients))}\n\n"
            f"**Menu classification:** {dietary}\n\n"
            f"**Allergens:** {escape(', '.join(item.allergens) or 'None listed')}\n\n"
            + ("**Why it fits:** " + escape(". ".join(dict.fromkeys(reasons))) if reasons else "")
        )
    if active.allergens and selection.item_ids:
        lines.append(ALLERGEN_QUALIFICATION)
    return "\n\n".join(lines)


def saved_preferences(profile: list[dict]) -> str:
    lines = []
    for p in profile:
        subject, value = escape(p["subject"]), p["value"]
        if p["dimension"] in {"ingredient", "cuisine", "dish"}:
            lines.append(f"You {'like' if value == 'like' else 'dislike'} {subject}.")
        elif p["dimension"] == "diet":
            lines.append(f"You follow a {subject} diet.")
        elif p["dimension"] == "allergy":
            lines.append(f"You avoid {subject} because of an allergy.")
        elif p["dimension"] == "budget":
            lines.append(f"Your usual budget is up to {escape(value)} SAR per dish.")
        elif p["dimension"] == "spice":
            level = ["no spice", "mild", "medium", "hot"][int(value)]
            lines.append(f"You prefer {level} dishes.")
    return " ".join(lines) or "You haven’t told me your preferences yet."


def memory_view(profile: list[dict], temporary: Constraints) -> str:
    return (
        "**Remembered across conversations**\n\n"
        + saved_preferences(profile)
        + "\n\n**This ordering request only**\n\n"
        + constraint_text(temporary)
    )
