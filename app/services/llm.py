from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from app.services.config import LLMSettings
from app.services.runtime_logging import (
    append_llm_trace,
    console_error,
    console_info,
    console_warn,
)


class LLMGateway:
    def __init__(self, settings: LLMSettings, enabled: bool = True) -> None:
        self.settings = settings
        self.enabled = enabled and bool(settings.api_key)
        self._client = None
        self.request_count = 0
        self.timeout_seconds = settings.timeout_seconds
        self._semaphore = asyncio.Semaphore(max(1, settings.max_concurrency))

        if self.enabled:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=settings.api_key,
                    base_url=settings.base_url,
                    timeout=self.timeout_seconds,
                )
                console_info(
                    f"[LLM] enabled=True model={settings.model} base_url={settings.base_url} "
                    f"timeout={self.timeout_seconds}s max_concurrency={settings.max_concurrency} "
                    f"retries={settings.retry_attempts}",
                )
            except Exception as exc:
                console_error(f"[LLM] failed to initialize client: {exc}")
                self.enabled = False
        else:
            console_warn("[LLM] enabled=False; using fallback heuristics")

    async def complete_json(self, prompt: str) -> dict[str, Any] | None:
        if not self.enabled or not self._client:
            return None
        self.request_count += 1
        request_id = self.request_count
        self._warn_unresolved_placeholders(prompt, request_id)
        text = await self._complete_with_retry(
            request_id=request_id,
            kind="json",
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            prompt_for_log=prompt,
        )
        if text is None:
            return None
        parsed = self.extract_json(text)
        if parsed is None:
            console_warn(f"[LLM][{request_id}] json parse failed; see the current event llm_io.log file")
        return parsed

    async def complete_text(self, prompt: str, system_prompt: str | None = None) -> str | None:
        if not self.enabled or not self._client:
            return None
        self.request_count += 1
        request_id = self.request_count
        self._warn_unresolved_placeholders(prompt, request_id)
        if system_prompt:
            self._warn_unresolved_placeholders(system_prompt, request_id)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        full_prompt = f"SYSTEM:\n{system_prompt or ''}\n\nUSER:\n{prompt}"
        return await self._complete_with_retry(
            request_id=request_id,
            kind="text",
            messages=messages,
            prompt_for_log=full_prompt,
        )

    async def _complete_with_retry(
        self,
        request_id: int,
        kind: str,
        messages: list[dict[str, str]],
        prompt_for_log: str,
    ) -> str | None:
        attempts = max(1, self.settings.retry_attempts + 1)
        last_error: str | None = None
        started_at = time.perf_counter()

        for attempt in range(1, attempts + 1):
            try:
                async with self._semaphore:
                    response = await self._client.chat.completions.create(
                        model=self.settings.model,
                        messages=messages,
                        temperature=0.2,
                    )
                text = response.choices[0].message.content or ""
                append_llm_trace(request_id, kind, prompt_for_log, output=text)
                return text
            except asyncio.TimeoutError:
                elapsed = time.perf_counter() - started_at
                last_error = f"Timeout after {elapsed:.2f}s"
                if attempt < attempts:
                    backoff = self.settings.retry_backoff_seconds * attempt
                    console_warn(
                        f"[LLM][{request_id}] timeout on attempt {attempt}/{attempts}; retrying in {backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)
                    continue
                console_warn(f"[LLM][{request_id}] timeout after {elapsed:.2f}s")
            except Exception as exc:
                elapsed = time.perf_counter() - started_at
                last_error = str(exc)
                if attempt < attempts:
                    backoff = self.settings.retry_backoff_seconds * attempt
                    console_warn(
                        f"[LLM][{request_id}] error on attempt {attempt}/{attempts}: {exc}; retrying in {backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)
                    continue
                console_error(f"[LLM][{request_id}] error after {elapsed:.2f}s: {exc}")
            break

        append_llm_trace(request_id, kind, prompt_for_log, error=last_error or "Unknown error")
        return None

    @staticmethod
    def extract_json(text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _warn_unresolved_placeholders(text: str, request_id: int) -> None:
        unresolved = sorted(set(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text)))
        if not unresolved:
            return
        console_warn(
            f"[LLM][{request_id}] unresolved template placeholders detected: {', '.join(unresolved)}; see the current event llm_io.log file"
        )
