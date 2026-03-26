from __future__ import annotations

ANSI_RESET = "\x1b[0m"
ANSI_TITLE = "\x1b[38;5;111m"
ANSI_ACCENT = "\x1b[38;5;111m"
ANSI_MUTED = "\x1b[38;5;245m"
ANSI_NOTICE = "\x1b[38;5;114m"
ANSI_SELECTED = "\x1b[1;38;5;16;48;5;117m"
ANSI_MESSAGE = "\x1b[38;5;223m"
ANSI_CREDIT = "\x1b[38;5;244m"

TITLE_ART = [
    "██████╗░███████╗░██████╗██╗░░░██╗███╗░░░███╗███████╗  ██████╗░██╗░░░██╗██╗██╗░░░░░██████╗░███████╗██████╗░",
    "██╔══██╗██╔════╝██╔════╝██║░░░██║████╗░████║██╔════╝  ██╔══██╗██║░░░██║██║██║░░░░░██╔══██╗██╔════╝██╔══██╗",
    "██████╔╝█████╗░░╚█████╗░██║░░░██║██╔████╔██║█████╗░░  ██████╦╝██║░░░██║██║██║░░░░░██║░░██║█████╗░░██████╔╝",
    "██╔══██╗██╔══╝░░░╚═══██╗██║░░░██║██║╚██╔╝██║██╔══╝░░  ██╔══██╗██║░░░██║██║██║░░░░░██║░░██║██╔══╝░░██╔══██╗",
    "██║░░██║███████╗██████╔╝╚██████╔╝██║░╚═╝░██║███████╗  ██████╦╝╚██████╔╝██║███████╗██████╔╝███████╗██║░░██║",
    "╚═╝░░╚═╝╚══════╝╚═════╝░░╚═════╝░╚═╝░░░░░╚═╝╚══════╝  ╚═════╝░░╚═════╝░╚═╝╚══════╝╚═════╝░╚══════╝╚═╝░░╚═╝",
]
TITLE_RULE_PREFIX = "── v0.0.1 "
TITLE_RULE_BODY = "─" * 79
TITLE_CREDIT_PREFIX = " by "
TITLE_CREDIT_NAME = "Frank Shan"
TITLE_CREDIT_SUFFIX = " ──"
TITLE_RULE_LINE = (
    TITLE_RULE_PREFIX + TITLE_RULE_BODY + TITLE_CREDIT_PREFIX + TITLE_CREDIT_NAME + TITLE_CREDIT_SUFFIX
)


def header_lines() -> list[str]:
    return [*TITLE_ART, TITLE_RULE_LINE, ""]


def box_lines(title: str, lines: list[str]) -> list[str]:
    safe_lines = lines or [""]
    inner_width = max(len(title) + 2, *(len(line) for line in safe_lines)) + 2
    title_text = f" {title} "
    top = "┌" + title_text + ("─" * (inner_width - len(title_text))) + "┐"
    content = [f"│ {line.ljust(inner_width - 2)} │" for line in safe_lines]
    bottom = "└" + ("─" * inner_width) + "┘"
    return [top, *content, bottom]


def render_ansi(text: str, *, message_mode: bool = False) -> str:
    styled_lines: list[str] = []
    for line in text.splitlines():
        if line == TITLE_RULE_LINE:
            styled_lines.append(
                f"{ANSI_TITLE}{TITLE_RULE_PREFIX}{TITLE_RULE_BODY}{TITLE_CREDIT_PREFIX}{ANSI_RESET}"
                f"{ANSI_CREDIT}{TITLE_CREDIT_NAME}{ANSI_RESET}"
                f"{ANSI_TITLE}{TITLE_CREDIT_SUFFIX}{ANSI_RESET}"
            )
            continue
        if line in TITLE_ART:
            styled_lines.append(f"{ANSI_TITLE}{line}{ANSI_RESET}")
            continue
        if line.startswith("┌") or line.startswith("└"):
            styled_lines.append(f"{ANSI_ACCENT}{line}{ANSI_RESET}")
            continue
        if line.startswith("│ >"):
            styled_lines.append(f"{ANSI_SELECTED}{line}{ANSI_RESET}")
            continue
        if line.startswith("│"):
            styled_lines.append(
                f"{ANSI_ACCENT}│{ANSI_RESET}"
                + line[1:-1]
                + f"{ANSI_ACCENT}{line[-1]}{ANSI_RESET}"
            )
            continue
        if line.startswith("keys:"):
            styled_lines.append(f"{ANSI_MUTED}{line}{ANSI_RESET}")
            continue
        if line.startswith("status:"):
            styled_lines.append(f"{ANSI_NOTICE}{line}{ANSI_RESET}")
            continue
        if message_mode and line:
            styled_lines.append(f"{ANSI_MESSAGE}{line}{ANSI_RESET}")
            continue
        styled_lines.append(line)
    return "\n".join(styled_lines)
