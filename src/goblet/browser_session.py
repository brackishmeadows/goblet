from __future__ import annotations

import base64
import pickle
from dataclasses import dataclass
from typing import Any

from .labyrinth import (
    LabyrinthPostSession,
    new_labyrinth_post_session,
    render_labyrinth_post_session,
    step_labyrinth_post_session,
)


SAVE_PREFIX = "GOBLET_LABYRINTH_SAVE_V1:"
PACKET_VERSION = 1


@dataclass
class BrowserSession:
    session: LabyrinthPostSession
    transcript: list[str]


def start(seed: str | int | None = None) -> dict[str, Any]:
    session = new_labyrinth_post_session(seed)
    lines: list[str] = []
    if session.random_seed is not None:
        lines.append(f"random seed: {session.random_seed}")
    lines.append("Liar's Labyrinth")
    lines.append("")
    lines.extend(step_labyrinth_post_session(session, None))
    browser_session = BrowserSession(session=session, transcript=list(lines))
    return packet(browser_session, lines)


def show(save_data: str) -> dict[str, Any]:
    browser_session = decode_session(save_data)
    lines = render_labyrinth_post_session(browser_session.session)
    return packet(browser_session, lines)


def step(save_data: str, command: str) -> dict[str, Any]:
    browser_session = decode_session(save_data)
    lines = step_labyrinth_post_session(browser_session.session, command)
    if lines:
        if browser_session.transcript:
            browser_session.transcript.append("")
        browser_session.transcript.extend(lines)
    return packet(browser_session, lines)


def export_transcript(save_data: str) -> str:
    browser_session = decode_session(save_data)
    return "\n".join(browser_session.transcript).rstrip() + "\n"


def encode_session(browser_session: BrowserSession) -> str:
    payload = pickle.dumps(browser_session)
    encoded = base64.b64encode(payload).decode("ascii")
    return SAVE_PREFIX + encoded


def decode_session(save_data: str) -> BrowserSession:
    if not save_data.startswith(SAVE_PREFIX):
        raise ValueError("unsupported labyrinth browser save format")
    encoded = save_data[len(SAVE_PREFIX):]
    try:
        payload = base64.b64decode(encoded.encode("ascii"))
        browser_session = pickle.loads(payload)
    except Exception as exc:
        raise ValueError("could not decode labyrinth browser save") from exc
    if not isinstance(browser_session, BrowserSession):
        raise ValueError("not a labyrinth browser save")
    return browser_session


def packet(browser_session: BrowserSession, lines: list[str]) -> dict[str, Any]:
    return {
        "version": PACKET_VERSION,
        "seed": browser_session.session.random_seed,
        "status": session_status(browser_session.session),
        "save_data": encode_session(browser_session),
        "lines": lines,
        "transcript": export_transcript_from_session(browser_session),
    }


def export_transcript_from_session(browser_session: BrowserSession) -> str:
    if not browser_session.transcript:
        return ""
    return "\n".join(browser_session.transcript).rstrip() + "\n"


def session_status(session: LabyrinthPostSession) -> str:
    if session.resigned:
        return "resigned"
    if session.state.escaped:
        return "escaped"
    if not session.state.player.alive:
        return "dead"
    return "playing"
