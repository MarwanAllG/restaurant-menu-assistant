"""Chainlit history is a projection of LangGraph checkpoints, never a second transcript."""

from __future__ import annotations

import json
from contextvars import ContextVar
from uuid import NAMESPACE_URL, uuid5

from chainlit.context import ChainlitContextException, context
from chainlit.data.base import BaseDataLayer
from chainlit.types import PageInfo, PaginatedResponse
from chainlit.user import PersistedUser

# Chainlit calls get_user only after verifying a JWT, or create_user after successful login.
# HTTP handlers lack a websocket context; this request-local principal bridges those calls.
principal: ContextVar[str | None] = ContextVar("restaurant-menu-assistant_principal", default=None)


class CheckpointDataLayer(BaseDataLayer):
    def __init__(self, assistant):
        self.assistant = assistant
        self.repo = assistant.repo

    def _uid(self) -> str:
        try:
            user = context.session.user
        except ChainlitContextException:
            user = None
        if user is not None:
            record = self.repo.get_user(user.identifier)
            if record:
                return record["id"]
        uid = principal.get()
        if not uid:
            raise PermissionError("Authentication required before loading history")
        return uid

    @staticmethod
    def _persisted(row):
        return PersistedUser(
            id=row["id"],
            identifier=row["identifier"],
            createdAt=row["created_at"],
            metadata={"provider": "credentials"},
        )

    async def get_user(self, identifier):
        row = self.repo.get_user(identifier)
        if row:
            principal.set(row["id"])
            return self._persisted(row)
        principal.set(None)
        return None

    async def create_user(self, user):
        row = self.repo.user(user.identifier)
        principal.set(row["id"])
        return self._persisted(row)

    async def get_thread_author(self, thread_id):
        uid = self._uid()
        try:
            self.repo.owned(thread_id, uid)
        except PermissionError:
            return ""
        with self.repo.connect() as db:
            row = db.execute("SELECT identifier FROM users WHERE id=?", (uid,)).fetchone()
        return row["identifier"] if row else ""

    def _thread_metadata(self, row):
        with self.repo.connect() as db:
            user = db.execute(
                "SELECT identifier FROM users WHERE id=?", (row["user_id"],)
            ).fetchone()
        return {
            "id": row["id"],
            "createdAt": row["created_at"],
            "name": row["name"],
            "userId": row["user_id"],
            "userIdentifier": user["identifier"],
            "metadata": json.loads(row["metadata"]),
            "tags": [],
            "steps": [],
            "elements": [],
        }

    async def get_thread(self, thread_id):
        uid = self._uid()
        try:
            row = self.repo.owned(thread_id, uid)
        except PermissionError:
            return None
        # Ownership is checked before this call reads any checkpoint.
        state = self.assistant.state(uid, thread_id)
        result = self._thread_metadata(row)
        for msg in state.get("messages", []):
            if msg.type not in {"human", "ai"}:
                continue
            result["steps"].append(
                {
                    "id": str(uuid5(NAMESPACE_URL, msg.id)),
                    "threadId": thread_id,
                    "type": "user_message" if msg.type == "human" else "assistant_message",
                    "name": result["userIdentifier"]
                    if msg.type == "human"
                    else "Marwan's Resturant",
                    "output": msg.content,
                    "input": "",
                    "metadata": {},
                    "createdAt": msg.additional_kwargs.get("created_at", row["created_at"]),
                    "streaming": False,
                    "isError": False,
                }
            )
        return result

    async def list_threads(self, pagination, filters):
        uid = self._uid()
        if filters.userId != uid:
            raise PermissionError("Cannot list another user's conversations")
        rows = self.repo.list_conversations(uid)
        if filters.search:
            rows = [r for r in rows if filters.search.casefold() in r["name"].casefold()]
        offset = 0
        if pagination.cursor:
            offset = next(
                (i + 1 for i, r in enumerate(rows) if r["id"] == pagination.cursor), len(rows)
            )
        page = rows[offset : offset + min(pagination.first, 100)]
        return PaginatedResponse(
            pageInfo=PageInfo(
                hasNextPage=offset + len(page) < len(rows),
                startCursor=page[0]["id"] if page else None,
                endCursor=page[-1]["id"] if page else None,
            ),
            data=[self._thread_metadata(r) for r in page],
        )

    async def update_thread(self, thread_id, name=None, user_id=None, metadata=None, tags=None):
        uid = self._uid()
        if user_id and user_id != uid:
            raise PermissionError("Cannot transfer conversation ownership")
        self.repo.owned(thread_id, uid)
        # Session metadata must never become an authentication or graph-state source.
        allowed = {
            k: v for k, v in (metadata or {}).items() if k in {"chat_profile", "chat_settings"}
        }
        self.repo.update_conversation(
            thread_id, uid, name, allowed if metadata is not None else None
        )

    async def delete_thread(self, thread_id):
        uid = self._uid()
        with self.assistant._lock:
            self.repo.owned(thread_id, uid)
            self.assistant.checkpointer.delete_thread(thread_id)
            self.repo.delete_conversation(thread_id, uid)

    # Optional UI persistence is intentionally disabled. No message/element duplicates.
    async def create_step(self, step_dict):
        pass

    async def update_step(self, step_dict):
        pass

    async def delete_step(self, step_id):
        pass

    async def create_element(self, element):
        pass

    async def get_element(self, thread_id, element_id):
        return None

    async def delete_element(self, element_id, thread_id=None):
        pass

    async def upsert_feedback(self, feedback):
        return ""

    async def delete_feedback(self, feedback_id):
        return False

    async def get_favorite_steps(self, user_id):
        return []

    async def build_debug_url(self):
        return ""

    async def close(self):
        self.assistant.close()
