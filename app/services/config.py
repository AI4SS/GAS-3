from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent
API_EXAMPLE = WORKSPACE_ROOT / "api-example.txt"
SETTINGS_FILE = ROOT / "config" / "settings.yaml"


class LLMSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    api_type: str = "openai"
    max_concurrency: int = 6
    timeout_seconds: float = 25.0
    retry_attempts: int = 2
    retry_backoff_seconds: float = 1.5


class RuntimeSettings(BaseModel):
    total_rounds: int = 7
    results_dir: str = "results"
    use_llm: bool = True
    dataset_path: str = "path/to/benchmark_events.json"
    event_id: int = 7
    group_concurrency: int = 6


class AppSettings(BaseModel):
    llm: LLMSettings = LLMSettings()
    runtime: RuntimeSettings = RuntimeSettings()


def _parse_api_example(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("sk-"):
            data["api_key"] = line
        elif line.startswith("default_model:"):
            data["model"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("base_url:"):
            data["base_url"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("http://") or line.startswith("https://"):
            data["base_url"] = line.strip().strip('"')
    return data


def load_settings() -> AppSettings:
    load_dotenv()
    payload: dict = {}
    if SETTINGS_FILE.exists():
        payload = yaml.safe_load(SETTINGS_FILE.read_text()) or {}

    api_example = _parse_api_example(API_EXAMPLE)
    llm_payload = payload.get("llm", {})
    runtime_payload = payload.get("runtime", {})

    dataset_path = str(os.getenv("SIM_DATASET_PATH") or runtime_payload.get("dataset_path") or RuntimeSettings().dataset_path)
    dataset_path_obj = Path(dataset_path)
    if not dataset_path_obj.is_absolute():
        dataset_path_obj = ROOT / dataset_path_obj

    llm = LLMSettings(
        api_key=os.getenv("DEEPSEEK_API_KEY") or llm_payload.get("api_key") or api_example.get("api_key", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL") or llm_payload.get("base_url") or api_example.get("base_url", ""),
        model=os.getenv("DEEPSEEK_MODEL") or llm_payload.get("model") or api_example.get("model", "deepseek-chat"),
        api_type=llm_payload.get("api_type", "openai"),
        max_concurrency=int(os.getenv("SIM_LLM_MAX_CONCURRENCY") or llm_payload.get("max_concurrency", 6)),
        timeout_seconds=float(os.getenv("SIM_LLM_TIMEOUT_SECONDS") or llm_payload.get("timeout_seconds", 25.0)),
        retry_attempts=int(os.getenv("SIM_LLM_RETRY_ATTEMPTS") or llm_payload.get("retry_attempts", 2)),
        retry_backoff_seconds=float(
            os.getenv("SIM_LLM_RETRY_BACKOFF_SECONDS") or llm_payload.get("retry_backoff_seconds", 1.5)
        ),
    )
    runtime = RuntimeSettings(
        total_rounds=int(os.getenv("SIM_TOTAL_ROUNDS") or runtime_payload.get("total_rounds", 7)),
        results_dir=runtime_payload.get("results_dir", "results"),
        use_llm=str(os.getenv("SIM_USE_LLM") or runtime_payload.get("use_llm", True)).lower() not in {"0", "false", "no"},
        dataset_path=str(dataset_path_obj),
        event_id=int(os.getenv("SIM_EVENT_ID") or runtime_payload.get("event_id", 7)),
        group_concurrency=int(os.getenv("SIM_GROUP_CONCURRENCY") or runtime_payload.get("group_concurrency", 6)),
    )
    return AppSettings(llm=llm, runtime=runtime)
