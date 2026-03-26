from __future__ import annotations

import shutil

from wcwidth import wcswidth

ANSI_RESET = "\x1b[0m"
ANSI_TITLE = "\x1b[38;5;111m"
ANSI_ACCENT = "\x1b[38;5;111m"
ANSI_MUTED = "\x1b[38;5;245m"
ANSI_NOTICE = "\x1b[38;5;114m"
ANSI_SELECTED = "\x1b[1;38;5;16;48;5;117m"
ANSI_MESSAGE = "\x1b[38;5;223m"
ANSI_CREDIT = "\x1b[38;5;244m"
ANSI_BOLD = "\x1b[1m"
ANSI_KEY = "\x1b[1;38;5;117m"
ANSI_LABEL = "\x1b[1;38;5;223m"
ANSI_VALUE = "\x1b[38;5;153m"

TITLE_ART = [
    "██████╗░███████╗░██████╗██╗░░░██╗███╗░░░███╗███████╗  ██████╗░██╗░░░██╗██╗██╗░░░░░██████╗░███████╗██████╗░",
    "██╔══██╗██╔════╝██╔════╝██║░░░██║████╗░████║██╔════╝  ██╔══██╗██║░░░██║██║██║░░░░░██╔══██╗██╔════╝██╔══██╗",
    "██████╔╝█████╗░░╚█████╗░██║░░░██║██╔████╔██║█████╗░░  ██████╦╝██║░░░██║██║██║░░░░░██║░░██║█████╗░░██████╔╝",
    "██╔══██╗██╔══╝░░░╚═══██╗██║░░░██║██║╚██╔╝██║██╔══╝░░  ██╔══██╗██║░░░██║██║██║░░░░░██║░░██║██╔══╝░░██╔══██╗",
    "██║░░██║███████╗██████╔╝╚██████╔╝██║░╚═╝░██║███████╗  ██████╦╝╚██████╔╝██║███████╗██████╔╝███████╗██║░░██║",
    "╚═╝░░╚═╝╚══════╝╚═════╝░░╚═════╝░╚═╝░░░░░╚═╝╚══════╝  ╚═════╝░░╚═════╝░╚═╝╚══════╝╚═════╝░╚══════╝╚═╝░░╚═╝",
]
TITLE_RULE_PREFIX = "── v0.0.2 "
TITLE_RULE_BODY = "─" * 79
TITLE_CREDIT_PREFIX = " by "
TITLE_CREDIT_NAME = "Frank Shan"
TITLE_CREDIT_SUFFIX = " ──"
TITLE_RULE_LINE = (
    TITLE_RULE_PREFIX + TITLE_RULE_BODY + TITLE_CREDIT_PREFIX + TITLE_CREDIT_NAME + TITLE_CREDIT_SUFFIX
)

MARKUP_KEY_OPEN = "\x01k"
MARKUP_KEY_CLOSE = "\x02k"
MARKUP_LABEL_OPEN = "\x01l"
MARKUP_LABEL_CLOSE = "\x02l"
MARKUP_VALUE_OPEN = "\x01v"
MARKUP_VALUE_CLOSE = "\x02v"
MARKUP_BOLD_OPEN = "\x01b"
MARKUP_BOLD_CLOSE = "\x02b"


def header_lines() -> list[str]:
    return [*TITLE_ART, TITLE_RULE_LINE, ""]


def box_lines(title: str, lines: list[str]) -> list[str]:
    safe_lines = lines or [""]
    terminal_columns = shutil.get_terminal_size(fallback=(120, 40)).columns
    max_inner_width = max(24, terminal_columns - 6)
    wrapped_lines: list[str] = []
    for line in safe_lines:
        wrapped_lines.extend(_wrap_visible_line(line, max_inner_width - 2))

    inner_width = min(
        max_inner_width,
        max(_display_width(title) + 2, *(_display_width(line) for line in wrapped_lines)) + 2,
    )
    title_text = f" {title} "
    top = "┌" + title_text + ("─" * (inner_width - len(title_text))) + "┐"
    content = [f"│ {_pad_visible(line, inner_width - 2)} │" for line in wrapped_lines]
    bottom = "└" + ("─" * inner_width) + "┘"
    return [top, *content, bottom]


def render_ansi(text: str, *, message_mode: bool = False) -> str:
    styled_lines: list[str] = []
    for line in text.splitlines():
        if line == TITLE_RULE_LINE:
            styled_lines.append(_apply_inline_markup(
                f"{ANSI_TITLE}{TITLE_RULE_PREFIX}{TITLE_RULE_BODY}{TITLE_CREDIT_PREFIX}{ANSI_RESET}"
                f"{ANSI_CREDIT}{TITLE_CREDIT_NAME}{ANSI_RESET}"
                f"{ANSI_TITLE}{TITLE_CREDIT_SUFFIX}{ANSI_RESET}"
            ))
            continue
        if line in TITLE_ART:
            styled_lines.append(_apply_inline_markup(f"{ANSI_TITLE}{line}{ANSI_RESET}"))
            continue
        if line.startswith("┌") or line.startswith("└"):
            styled_lines.append(_apply_inline_markup(f"{ANSI_ACCENT}{line}{ANSI_RESET}"))
            continue
        if line.startswith("│ >"):
            styled_lines.append(_apply_inline_markup(f"{ANSI_SELECTED}{line}{ANSI_RESET}"))
            continue
        if line.startswith("│"):
            styled_lines.append(_apply_inline_markup(
                f"{ANSI_ACCENT}│{ANSI_RESET}"
                + line[1:-1]
                + f"{ANSI_ACCENT}{line[-1]}{ANSI_RESET}"
            ))
            continue
        if line.startswith("keys:"):
            styled_lines.append(_apply_inline_markup(f"{ANSI_MUTED}{line}{ANSI_RESET}"))
            continue
        if line.startswith("status:"):
            styled_lines.append(_apply_inline_markup(f"{ANSI_NOTICE}{line}{ANSI_RESET}"))
            continue
        if message_mode and line:
            styled_lines.append(_apply_inline_markup(f"{ANSI_MESSAGE}{line}{ANSI_RESET}"))
            continue
        styled_lines.append(_apply_inline_markup(line))
    return "\n".join(styled_lines)


def _apply_inline_markup(text: str) -> str:
    return (
        text.replace(MARKUP_KEY_OPEN, ANSI_KEY)
        .replace(MARKUP_KEY_CLOSE, ANSI_RESET)
        .replace(MARKUP_LABEL_OPEN, ANSI_LABEL)
        .replace(MARKUP_LABEL_CLOSE, ANSI_RESET)
        .replace(MARKUP_VALUE_OPEN, ANSI_VALUE)
        .replace(MARKUP_VALUE_CLOSE, ANSI_RESET)
        .replace(MARKUP_BOLD_OPEN, ANSI_BOLD)
        .replace(MARKUP_BOLD_CLOSE, ANSI_RESET)
    )


def _display_width(text: str) -> int:
    return max(0, wcswidth(_strip_markup(text)))


def _strip_markup(text: str) -> str:
    return (
        text.replace(MARKUP_KEY_OPEN, "")
        .replace(MARKUP_KEY_CLOSE, "")
        .replace(MARKUP_LABEL_OPEN, "")
        .replace(MARKUP_LABEL_CLOSE, "")
        .replace(MARKUP_VALUE_OPEN, "")
        .replace(MARKUP_VALUE_CLOSE, "")
        .replace(MARKUP_BOLD_OPEN, "")
        .replace(MARKUP_BOLD_CLOSE, "")
    )


def _pad_visible(text: str, width: int) -> str:
    padding = max(0, width - _display_width(text))
    return text + (" " * padding)


def _wrap_visible_line(text: str, width: int) -> list[str]:
    if width <= 0:
        return [""]
    if _display_width(text) <= width:
        return [text]

    lines: list[str] = []
    current = ""
    current_width = 0
    index = 0
    while index < len(text):
        token = _next_token(text, index)
        index += len(token)
        token_width = 0 if _is_markup_token(token) else max(0, wcswidth(token))

        if token_width > 0 and current_width > 0 and current_width + token_width > width:
            lines.append(current.rstrip())
            current = ""
            current_width = 0
            if token == " ":
                continue

        current += token
        current_width += token_width

    if current or not lines:
        lines.append(current.rstrip())
    return lines


def _next_token(text: str, index: int) -> str:
    if text[index] in {"\x01", "\x02"} and index + 1 < len(text):
        return text[index : index + 2]
    return text[index]


def _is_markup_token(token: str) -> bool:
    return len(token) == 2 and token[0] in {"\x01", "\x02"}
