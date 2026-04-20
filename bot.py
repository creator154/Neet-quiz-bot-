#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import importlib.util
import json
import random
import re
import urllib.parse
import sys
from contextlib import closing, suppress
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputTextMessageContent, Poll, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, InlineQueryHandler
from telegram import InlineQueryResultArticle

BASE_PATH = Path(__file__).resolve().with_name("bot_base.py")
spec = importlib.util.spec_from_file_location("bot_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load bot_base.py from {BASE_PATH}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


# ============================================================
# Advanced overlay: feasible additions without OCR / paid APIs
# ============================================================

CHECKMARKS = ("✅", "☑", "✔", "✓")
TEXT_IMPORT_STATES = {"adv_await_import_text", "adv_await_clone_source"}
SPEED_PRESETS = {
    "slow": (1.50, "slow"),
    "normal": (1.00, "normal"),
    "fast": (0.75, "fast"),
}
OPTION_RE = re.compile(r"^\s*(?:[-*•]|\(?[A-Ja-j1-9]\)|[A-Ja-j1-9][\).:-])\s*(.+?)\s*$")
ANSWER_RE = re.compile(r"^\s*(?:answer|ans|correct|right)\s*[:\-]\s*(.+?)\s*$", re.I)
EXPL_RE = re.compile(r"^\s*(?:explanation|explain|reason|note)\s*[:\-]\s*(.+?)\s*$", re.I)
QUESTION_PREFIX_RE = re.compile(r"^\s*(?:Q(?:uestion)?\s*\d+|\d+)\s*[\).:\-]\s*", re.I)
COUNTER_RE = re.compile(r"^\s*[\[(]?\s*\d+\s*/\s*\d+\s*[\])]?\s*", re.I)
URL_RE = re.compile(r"(?:https?://\S+|t\.me/\S+)", re.I)
USERNAME_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{3,}")
QUIZBOT_TOKEN_RE = re.compile(r"(?:@quizbot\s+)?quiz\s*:\s*([A-Za-z0-9_-]{4,})", re.I)


def ensure_column(table: str, column: str, definition: str) -> None:
    with closing(base.DBH.connect()) as conn:
        cols = {str(r["name"]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()


base.DBH.executescript(
    """
    CREATE TABLE IF NOT EXISTS draft_sections (
        draft_id TEXT NOT NULL,
        section_no INTEGER NOT NULL,
        title TEXT NOT NULL,
        start_q INTEGER NOT NULL,
        end_q INTEGER NOT NULL,
        question_time INTEGER,
        PRIMARY KEY (draft_id, section_no)
    );

    CREATE TABLE IF NOT EXISTS clone_sessions (
        user_id INTEGER PRIMARY KEY,
        draft_id TEXT NOT NULL,
        clone_token TEXT,
        source_text TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    );
    """
)
ensure_column("sessions", "speed_factor", "REAL DEFAULT 1.0")
ensure_column("sessions", "speed_mode", "TEXT DEFAULT 'normal'")
ensure_column("sessions", "paused_at", "INTEGER")
ensure_column("session_questions", "section_title", "TEXT")
ensure_column("session_questions", "question_time_override", "INTEGER")


base._FINAL_SUPPORTED_GROUP_COMMANDS = set(getattr(base, "_FINAL_SUPPORTED_GROUP_COMMANDS", set())) | {
    "pauseq",
    "resumeq",
    "skipq",
    "speed",
}


def clean_forwarded_text(text: str) -> str:
    value = base.normalize_visual_text(text or "")
    value = urllib.parse.unquote(value)
    value = COUNTER_RE.sub("", value)
    value = re.sub(r"\bvia\b\s+@?[A-Za-z0-9_]+", " ", value, flags=re.I)
    value = URL_RE.sub(" ", value)
    value = USERNAME_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -–—|•")



def _strip_checkmark(text: str) -> Tuple[str, bool]:
    raw = text or ""
    marked = any(mark in raw for mark in CHECKMARKS)
    for mark in CHECKMARKS:
        raw = raw.replace(mark, "")
    return base.normalize_visual_text(raw), marked



def question_signature(question: str, options: Iterable[str]) -> str:
    merged = " || ".join([clean_forwarded_text(question)] + [clean_forwarded_text(x) for x in options])
    merged = merged.casefold()
    merged = re.sub(r"\s+", " ", merged)
    return merged.strip()



def existing_question_signatures(draft_id: str) -> set[str]:
    seen: set[str] = set()
    for row in base.get_draft_questions(draft_id):
        opts = base.jload(row["options"], []) or []
        seen.add(question_signature(str(row["question"]), [str(x) for x in opts]))
    return seen



def dedup_add_question_to_draft(draft_id: str, question: str, options: List[str], correct_option: int, explanation: str, src: str) -> Tuple[bool, Optional[int]]:
    sig = question_signature(question, options)
    if sig in existing_question_signatures(draft_id):
        return False, None
    q_no = base.add_question_to_draft(draft_id, clean_forwarded_text(question), [clean_forwarded_text(o) for o in options], int(correct_option), clean_forwarded_text(explanation), src)
    return True, q_no



def parse_answer_ref(ref: str, options: List[str]) -> Optional[int]:
    raw = base.normalize_visual_text(ref or "")
    if not raw:
        return None
    raw_up = raw.upper()
    if len(raw_up) == 1 and "A" <= raw_up <= "J":
        idx = ord(raw_up) - ord("A")
        if idx < len(options):
            return idx
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return idx
    for idx, opt in enumerate(options):
        if base.normalize_visual_text(opt).casefold() == raw.casefold():
            return idx
    return None



def parse_marked_questions_from_text(text: str) -> List[Dict[str, Any]]:
    raw = (text or "").replace("\r", "")
    raw = raw.strip()
    if not raw:
        return []

    # JSON array support
    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            items: List[Dict[str, Any]] = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                q = clean_forwarded_text(str(item.get("question") or item.get("questions") or ""))
                opts = item.get("options") or []
                if isinstance(opts, dict):
                    opts = list(opts.values())
                opts = [clean_forwarded_text(str(x)) for x in opts if str(x).strip()]
                ans = parse_answer_ref(str(item.get("answer") or item.get("correct") or ""), opts)
                if q and len(opts) >= 2 and ans is not None:
                    items.append({
                        "question": q,
                        "options": opts,
                        "correct_option": ans,
                        "explanation": clean_forwarded_text(str(item.get("explanation") or "")),
                    })
            if items:
                return items
    except Exception:
        pass

    blocks = [b.strip() for b in re.split(r"\n\s*\n+", raw) if b.strip()]
    parsed: List[Dict[str, Any]] = []

    for block in blocks:
        lines = [base.normalize_visual_text(x) for x in block.split("\n") if base.normalize_visual_text(x)]
        if not lines:
            continue
        question_parts: List[str] = []
        options: List[str] = []
        answer_ref: Optional[str] = None
        explanation_parts: List[str] = []
        correct_option: Optional[int] = None

        for idx, line in enumerate(lines):
            ans_m = ANSWER_RE.match(line)
            if ans_m:
                answer_ref = ans_m.group(1).strip()
                continue
            expl_m = EXPL_RE.match(line)
            if expl_m:
                explanation_parts.append(expl_m.group(1).strip())
                continue
            opt_m = OPTION_RE.match(line)
            if opt_m:
                opt_text, marked = _strip_checkmark(opt_m.group(1).strip())
                if opt_text:
                    options.append(opt_text)
                    if marked:
                        correct_option = len(options) - 1
                continue
            if idx == 0 and not options:
                q_line = clean_forwarded_text(QUESTION_PREFIX_RE.sub("", line))
                if q_line:
                    question_parts.append(q_line)
                continue
            if options:
                # treat trailing free text as explanation or option continuation
                if explanation_parts:
                    explanation_parts.append(line)
                elif options:
                    options[-1] = base.normalize_visual_text(f"{options[-1]} {line}")
                continue
            question_parts.append(line)

        question = clean_forwarded_text(" ".join(question_parts))
        if correct_option is None and answer_ref is not None:
            correct_option = parse_answer_ref(answer_ref, options)
        if question and len(options) >= 2 and correct_option is not None:
            parsed.append(
                {
                    "question": question,
                    "options": options,
                    "correct_option": int(correct_option),
                    "explanation": clean_forwarded_text(" ".join(explanation_parts)),
                }
            )

    return parsed



def resolve_editable_draft(user_id: int, raw_code: str) -> Optional[Any]:
    code = base.normalize_visual_text(raw_code or "").upper()
    draft_id = code or (base.get_active_draft_id(user_id) or "")
    if not draft_id:
        return None
    draft = base.get_draft(draft_id)
    if not draft:
        return None
    if int(draft["owner_id"]) != user_id and not getattr(base, "is_all_access_admin", lambda _x: False)(user_id):
        return None
    return draft



def list_sections(draft_id: str) -> List[Any]:
    return base.DBH.fetchall("SELECT * FROM draft_sections WHERE draft_id=? ORDER BY section_no ASC", (draft_id,))



def set_section(draft_id: str, start_q: int, end_q: int, title: str, question_time: Optional[int]) -> None:
    next_no_row = base.DBH.fetchone("SELECT COALESCE(MAX(section_no), 0) AS mx FROM draft_sections WHERE draft_id=?", (draft_id,))
    next_no = int(next_no_row["mx"] if next_no_row else 0) + 1
    base.DBH.execute(
        "INSERT INTO draft_sections(draft_id, section_no, title, start_q, end_q, question_time) VALUES(?,?,?,?,?,?)",
        (draft_id, next_no, base.normalize_visual_text(title), int(start_q), int(end_q), int(question_time) if question_time else None),
    )



def clear_sections(draft_id: str) -> None:
    base.DBH.execute("DELETE FROM draft_sections WHERE draft_id=?", (draft_id,))



def apply_sections_to_session(session_id: str, draft_id: str) -> None:
    for row in list_sections(draft_id):
        base.DBH.execute(
            "UPDATE session_questions SET section_title=?, question_time_override=? WHERE session_id=? AND q_no BETWEEN ? AND ?",
            (
                row["title"],
                row["question_time"],
                session_id,
                int(row["start_q"]),
                int(row["end_q"]),
            ),
        )



def extract_clone_token(text: str) -> Optional[str]:
    raw = urllib.parse.unquote(base.normalize_visual_text(text or ""))
    m = QUIZBOT_TOKEN_RE.search(raw)
    if m:
        return m.group(1)
    m = re.search(r"(?:^|\b)quiz[:=]([A-Za-z0-9_-]{4,})", raw, flags=re.I)
    if m:
        return m.group(1)
    return None



def start_clone_session(user_id: int, draft_id: str, clone_token: str, source_text: str) -> None:
    base.DBH.execute(
        "INSERT OR REPLACE INTO clone_sessions(user_id, draft_id, clone_token, source_text, active, created_at, updated_at) VALUES(?,?,?,?,1,COALESCE((SELECT created_at FROM clone_sessions WHERE user_id=?),?),?)",
        (user_id, draft_id, clone_token, source_text, user_id, base.now_ts(), base.now_ts()),
    )



def get_clone_session(user_id: int) -> Optional[Any]:
    return base.DBH.fetchone("SELECT * FROM clone_sessions WHERE user_id=? AND active=1", (user_id,))



def stop_clone_session(user_id: int) -> None:
    base.DBH.execute("DELETE FROM clone_sessions WHERE user_id=?", (user_id,))



def format_draft_info(draft: Any) -> str:
    q_rows = base.get_draft_questions(draft["id"])
    sections = list_sections(draft["id"])
    lines = [
        f"<b>Draft Info</b>",
        f"Title: <b>{base.html_escape(draft['title'])}</b>",
        f"Code: <code>{draft['id']}</code>",
        f"Owner: <code>{draft['owner_id']}</code>",
        f"Questions: <b>{len(q_rows)}</b>",
        f"Time / question: <b>{draft['question_time']} sec</b>",
        f"Negative / wrong: <b>{draft['negative_mark']}</b>",
        f"Created: <b>{base.fmt_dt(draft['created_at'])}</b>",
        f"Updated: <b>{base.fmt_dt(draft['updated_at'])}</b>",
    ]
    if sections:
        lines.append("")
        lines.append("<b>Sections</b>")
        for row in sections:
            lines.append(
                f"• {base.html_escape(row['title'])} — Q{row['start_q']}-Q{row['end_q']}"
                + (f" — {row['question_time']} sec" if row["question_time"] else "")
            )
    return "\n".join(lines)



def delete_question_numbers(draft_id: str, q_numbers: List[int]) -> int:
    if not q_numbers:
        return 0
    with closing(base.DBH.connect()) as conn:
        removed = 0
        for q_no in sorted(set(int(x) for x in q_numbers), reverse=True):
            cur = conn.execute("DELETE FROM draft_questions WHERE draft_id=? AND q_no=?", (draft_id, q_no))
            removed += int(cur.rowcount or 0)
        rows = conn.execute("SELECT id, q_no FROM draft_questions WHERE draft_id=? ORDER BY q_no ASC", (draft_id,)).fetchall()
        for new_no, row in enumerate(rows, start=1):
            conn.execute("UPDATE draft_questions SET q_no=? WHERE id=?", (new_no, row["id"]))
        conn.commit()
    base.refresh_draft_status(draft_id)
    return removed



def parse_q_number_list(raw: str) -> List[int]:
    out: List[int] = []
    for part in re.split(r"\s*,\s*", raw.strip()):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                x, y = int(a), int(b)
                if x <= y:
                    out.extend(list(range(x, y + 1)))
            continue
        if part.isdigit():
            out.append(int(part))
    return sorted(set(out))



def shuffle_draft_questions(draft_id: str) -> None:
    rows = [dict(r) for r in base.get_draft_questions(draft_id)]
    if len(rows) < 2:
        return
    random.shuffle(rows)
    with closing(base.DBH.connect()) as conn:
        conn.execute("DELETE FROM draft_questions WHERE draft_id=?", (draft_id,))
        for idx, row in enumerate(rows, start=1):
            conn.execute(
                "INSERT INTO draft_questions(draft_id, q_no, question, options, correct_option, explanation, src) VALUES(?,?,?,?,?,?,?)",
                (
                    draft_id,
                    idx,
                    row["question"],
                    row["options"],
                    row["correct_option"],
                    row["explanation"],
                    row["src"],
                ),
            )
        conn.commit()
    base.refresh_draft_status(draft_id)



def copy_draft(draft_id: str, owner_id: int) -> str:
    draft = base.get_draft(draft_id)
    if not draft:
        raise ValueError("Draft not found")
    new_id = base.create_draft(owner_id, f"{draft['title']} (Copy)", int(draft['question_time']), float(draft['negative_mark']))
    for row in base.get_draft_questions(draft_id):
        base.add_question_to_draft(
            new_id,
            str(row["question"]),
            [str(x) for x in (base.jload(row["options"], []) or [])],
            int(row["correct_option"]),
            str(row["explanation"] or ""),
            str(row["src"] or "copy"),
        )
    for row in list_sections(draft_id):
        set_section(new_id, int(row["start_q"]), int(row["end_q"]), str(row["title"]), int(row["question_time"]) if row["question_time"] else None)
    return new_id


async def import_text_into_draft(message, context, draft_id: str, text: str, src: str = "text") -> None:
    parsed = parse_marked_questions_from_text(text)
    if not parsed:
        await base.safe_reply(
            message,
            "No valid questions were found. Supported format: one question block with options, and the correct option marked with ✅ or an Answer: line.",
        )
        return
    added = 0
    skipped = 0
    for item in parsed:
        ok, _q_no = dedup_add_question_to_draft(
            draft_id,
            item["question"],
            list(item["options"]),
            int(item["correct_option"]),
            str(item.get("explanation") or ""),
            src,
        )
        if ok:
            added += 1
        else:
            skipped += 1
    draft = base.get_draft(draft_id)
    await base.send_draft_card(
        context,
        message.chat.id,
        message.from_user.id,
        draft_id,
        header=f"✅ Text import complete. Added: {added} | Skipped duplicates: {skipped}",
    )
    if draft:
        base.audit(message.from_user.id, "import_text", draft_id, {"added": added, "skipped": skipped})


_previous_create_session_from_draft = base.create_session_from_draft

def create_session_from_draft(draft_id: str, chat_id: int, actor_id: int) -> Optional[str]:
    session_id = _previous_create_session_from_draft(draft_id, chat_id, actor_id)
    if session_id:
        apply_sections_to_session(session_id, draft_id)
        base.DBH.execute(
            "UPDATE sessions SET speed_factor=COALESCE(speed_factor, 1.0), speed_mode=COALESCE(speed_mode, 'normal'), paused_at=NULL WHERE id=?",
            (session_id,),
        )
    return session_id


base.create_session_from_draft = create_session_from_draft


async def begin_or_advance_exam(context, session_id: str) -> None:
    session = base.get_session(session_id)
    if not session or session["status"] != "running":
        return
    next_index = int(session["current_index"] or 0) + 1
    total = int(session["total_questions"] or 0)
    if next_index > total:
        await base.finish_exam(context, session_id, reason="completed")
        return
    q = base.get_session_question(session_id, next_index)
    if not q:
        await base.finish_exam(context, session_id, reason="missing_question")
        return
    options = base.jload(q["options"], []) or []
    section_title = base.normalize_visual_text(q["section_title"] or "")
    base_seconds = int(q["question_time_override"] or session["question_time"] or 30)
    speed_factor = float(session["speed_factor"] or 1.0)
    effective_seconds = max(5, int(round(base_seconds * speed_factor)))

    try:
        prefix_parts = [f"[{next_index}/{total}]"]
        if section_title:
            prefix_parts.append(f"[{section_title}]")
        prefix_parts.append(f"[{base.normalize_visual_text(session['title'])}]")
        question_prefix = " ".join(prefix_parts) + "\n"
        poll_question = (question_prefix + str(q["question"])).strip()
        if len(poll_question) > 300:
            allowed_q = max(10, 300 - len(question_prefix))
            poll_question = question_prefix + str(q["question"])[: allowed_q - 1].rstrip() + "…"
        explanation_text = base.normalize_visual_text(q["explanation"] or f"Question {next_index} of {total}")
        if len(explanation_text) > 200:
            explanation_text = explanation_text[:199] + "…"
        msg = await context.bot.send_poll(
            chat_id=session["chat_id"],
            question=poll_question,
            options=options,
            type=Poll.QUIZ,
            is_anonymous=False,
            allows_multiple_answers=False,
            correct_option_id=int(q["correct_option"]),
