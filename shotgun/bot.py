from __future__ import annotations

import logging

from nio import (
    AsyncClient,
    Event,
    MatrixRoom,
    RoomMemberEvent,
    RoomMessageText,
    RoomSendResponse,
    SyncResponse,
)

from .agent import run_agent
from .config import ShotgunConfig

PREFIX = "\u2692\ufe0f"  # ⚒️

logger = logging.getLogger("shotgun")


class ShotgunBot:
    def __init__(self, config: ShotgunConfig) -> None:
        self.config = config
        self.client = AsyncClient(
            config.matrix.homeserver,
            config.matrix.user_id,
        )
        self._own_events: set[str] = set()
        self._dm_rooms: set[str] = set()
        self._synced: bool = False

    async def start(self) -> None:
        resp = await self.client.login(self.config.matrix.access_token)
        if isinstance(resp, Exception):
            raise resp
        logger.info("Logged in as %s on %s", self.client.user_id, self.client.homeserver)

        self.client.add_event_callback(self._on_invite, RoomMemberEvent)
        self.client.add_event_callback(self._on_message, RoomMessageText)
        self.client.add_response_callback(self._on_sync_response, SyncResponse)

        await self.client.sync_forever(timeout=30_000)

    def _on_sync_response(self, _: SyncResponse) -> None:
        self._synced = True

    async def _on_invite(self, room: MatrixRoom, event: RoomMemberEvent) -> None:
        if event.membership != "invite":
            return
        if event.state_key != self.client.user_id:
            return
        await self.client.join(room.room_id)
        logger.info("Joined room %s", room.room_id)

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if event.sender == self.client.user_id:
            return
        if not self._synced:
            return

        if not self._should_respond(room, event):
            return

        await self._send_reply(room, event, f"{PREFIX} Agent started")
        self._own_events.add(event.event_id)

        zs_config = self.config.zerostack_dm if self._is_dm(room, event) and self.config.zerostack_dm else self.config.zerostack
        output, success = await run_agent(event.body, zs_config)
        if success:
            await self._send_reply(room, event, output)
        else:
            await self._send_reply(room, event, f"{PREFIX} Agent crashed:\n{output}")

    def _is_dm(self, room: MatrixRoom, event: RoomMessageText) -> bool:
        if room.room_id in self._dm_rooms:
            return True
        # Heuristic: joined member count ≤ 2
        if hasattr(room, "joined_count") and room.joined_count <= 2:
            self._dm_rooms.add(room.room_id)
            return True
        if len(room.users) <= 2:
            self._dm_rooms.add(room.room_id)
            return True
        return False

    def _is_mentioned(self, event: RoomMessageText) -> bool:
        user_id = self.client.user_id
        if user_id and user_id in event.body:
            return True
        # Also check just the localpart as a fallback
        if ":" in user_id:
            localpart = user_id.split(":")[0]
            if localpart in event.body:
                return True
        return False

    def _is_reply_to_bot(self, event: RoomMessageText) -> bool:
        relates = getattr(event, "relates_to", None)
        if not relates:
            return False
        in_reply_to = getattr(relates, "in_reply_to", None)
        if not in_reply_to:
            return False
        event_id = getattr(in_reply_to, "event_id", None)
        return event_id in self._own_events

    def _should_respond(self, room: MatrixRoom, event: RoomMessageText) -> bool:
        sender = event.sender
        is_dm = self._is_dm(room, event)
        filters = self.config.filters_dm if is_dm and self.config.filters_dm else self.config.filters

        if filters.denylist and sender in filters.denylist:
            return False
        if filters.allowlist and sender not in filters.allowlist:
            return False

        if is_dm:
            return self.config.allow_dm
        if self._is_mentioned(event):
            return True
        if self._is_reply_to_bot(event):
            return True

        return False

    async def _send_reply(self, room: MatrixRoom, event: Event, body: str) -> None:
        content = {
            "msgtype": "m.text",
            "body": body,
            "m.relates_to": {
                "m.in_reply_to": {
                    "event_id": event.event_id,
                },
            },
        }
        resp = await self.client.room_send(
            room.room_id,
            message_type="m.room.message",
            content=content,
        )
        if isinstance(resp, RoomSendResponse):
            self._own_events.add(resp.event_id)
