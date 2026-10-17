"""Run: uv run chainlit run app.py --host 0.0.0.0 --port 8000"""

import logging
import os

import chainlit as cl
from chainlit.config import config

from core.auth import authenticate
from core.config import Settings
from core.data_layer import CheckpointDataLayer
from core.render import memory_view
from core.schemas import Constraints
from core.workflow import Assistant

logging.basicConfig(level=logging.INFO)
assistant = Assistant(Settings.load())
# Render supplies its public URL; APP_URL supports another service or custom domain.
for origin in [os.getenv("APP_URL"), os.getenv("RENDER_EXTERNAL_URL")]:
    if origin:
        config.project.allow_origins.append(origin.rstrip("/"))


def identity():
    user = cl.user_session.get("user")
    if user is None:
        raise PermissionError("Sign in to continue")
    record = assistant.repo.get_user(user.identifier)
    if record is None:
        raise PermissionError("Authenticated user was not persisted")
    return record["id"], cl.context.session.thread_id


def memory_action():
    return cl.Action(name="remembered_preferences", label="Remembered preferences", payload={})


@cl.data_layer
def data_layer():
    return CheckpointDataLayer(assistant)


@cl.password_auth_callback
async def login(username: str, password: str):
    valid = await cl.make_async(authenticate)(username, password)
    if valid:
        return cl.User(identifier=username, metadata={"provider": "credentials"})
    return None


@cl.on_chat_start
async def start():
    cl.user_session.set("preferences_message", None)
    uid, tid = identity()
    assistant.new_conversation(uid, tid)
    await cl.Message(
        content="Welcome to **Marwan's Resturant**. Tell me what sounds good, and I’ll help you explore the menu.",
        actions=[memory_action()],
    ).send()


@cl.on_chat_resume
async def resume(thread):
    cl.user_session.set("preferences_message", None)
    uid, tid = identity()
    assistant.repo.owned(thread["id"], uid)
    if thread["id"] != tid:
        raise PermissionError("Conversation mismatch")
    # Checkpoints are already projected into thread.steps by the data layer.


@cl.on_message
async def on_message(message: cl.Message):
    uid, tid = identity()
    if message.content.strip().casefold() == "/preferences":
        await show_memory(None)
        return
    try:
        result = await cl.make_async(assistant.turn)(uid, tid, message.content, message.id)
        await cl.Message(content=result["response"], actions=[memory_action()]).send()
    except (ValueError, PermissionError) as exc:
        await cl.Message(content=str(exc)).send()
    except Exception as exc:  # noqa: BLE001 - keep UI responsive; log only exception type
        logging.getLogger(__name__).error("Turn failed: %s", type(exc).__name__)
        await cl.Message(
            content="I couldn’t finish that turn. Please try again; your stored preferences "
            "and conversation have been preserved."
        ).send()


@cl.action_callback("remembered_preferences")
async def show_memory(action):
    uid, tid = identity()
    state = await cl.make_async(assistant.state)(uid, tid)
    content = memory_view(
        assistant.repo.profile(uid), Constraints.model_validate(state.get("temporary", {}))
    )
    message = cl.user_session.get("preferences_message")
    if message is None:
        message = cl.Message(content=content)
        cl.user_session.set("preferences_message", message)
        await message.send()
    else:
        message.content = content
        await message.update()
