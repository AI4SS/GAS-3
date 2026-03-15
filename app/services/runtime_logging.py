from __future__ import annotations

from datetime import datetime
from pathlib import Path


RESET = "\033[0m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
WHITE = "\033[97m"

_LOG_DIR: Path | None = None
_LLM_LOG_FILE: Path | None = None


def init_log_dir(results_dir: str) -> None:
    global _LOG_DIR, _LLM_LOG_FILE
    _LOG_DIR = Path(results_dir) / "logs"
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LLM_LOG_FILE = _LOG_DIR / "llm_io.log"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def console_info(message: str, color: str = CYAN) -> None:
    print(f"{color}{message}{RESET}", flush=True)


def console_warn(message: str) -> None:
    console_info(message, color=YELLOW)


def console_error(message: str) -> None:
    console_info(message, color=RED)


def console_success(message: str) -> None:
    console_info(message, color=GREEN)


def console_stage(message: str) -> None:
    console_info(message, color=MAGENTA)


def console_round(message: str) -> None:
    console_info(message, color=BLUE)


def console_banner(title: str) -> None:
    line = "=" * 88
    print(f"{WHITE}{line}{RESET}", flush=True)
    print(f"{BLUE}{title}{RESET}", flush=True)
    print(f"{WHITE}{line}{RESET}", flush=True)


def console_phase(title: str, message: str) -> None:
    print(f"{MAGENTA}[{title}]{RESET} {message}", flush=True)


def console_group_panel(
    group_name: str,
    group_id: str,
    hierarchy_path: list[str],
    polarity: int,
    emotion: dict,
    attitude: dict,
    internal_groups: dict | None = None,
    metrics: dict | None = None,
    comment: str | None = None,
) -> None:
    path_text = " > ".join(hierarchy_path) if hierarchy_path else group_name
    print(f"{WHITE}----------------------------------------------------------------------------------------{RESET}", flush=True)
    print(f"{BLUE}[Group]{RESET} {group_name} ({group_id})", flush=True)
    print(f"{CYAN}  Path:{RESET} {path_text}", flush=True)
    print(f"{CYAN}  Polarity:{RESET} {polarity}", flush=True)
    print(f"{CYAN}  Emotion:{RESET} {emotion}", flush=True)
    print(f"{CYAN}  Attitude:{RESET} {attitude}", flush=True)
    if internal_groups is not None:
        print(f"{CYAN}  InternalGroups:{RESET} {internal_groups}", flush=True)
    if metrics is not None:
        print(f"{GREEN}  Metrics:{RESET} {metrics}", flush=True)
    if comment:
        print(f"{MAGENTA}  Comment:{RESET} {comment}", flush=True)


def console_parallel_status(message: str) -> None:
    console_info(message, color=YELLOW)


def append_llm_trace(request_id: int, kind: str, prompt: str, output: str | None = None, error: str | None = None) -> None:
    if _LLM_LOG_FILE is None:
        return
    with _LLM_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {_timestamp()} | REQUEST {request_id} | {kind.upper()} =====\n")
        handle.write("PROMPT:\n")
        handle.write(prompt)
        handle.write("\n")
        if output is not None:
            handle.write("\nOUTPUT:\n")
            handle.write(output)
            handle.write("\n")
        if error is not None:
            handle.write("\nERROR:\n")
            handle.write(error)
            handle.write("\n")
