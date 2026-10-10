import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .schema import blank_output_for_source_type, response_format_for_source_type, schema_fields_for_source_type


DEFAULT_MODEL_IDS = {
    "gemma-4-e2b": "google/gemma-4-e2b",
    "gemma-4-e4b": "google/gemma-4-e4b",
}

MODEL_ENV_KEYS = {
    "gemma-4-e2b": "LOCAL_GEMMA_E2B_LMSTUDIO_MODEL",
    "gemma-4-e4b": "LOCAL_GEMMA_E4B_LMSTUDIO_MODEL",
}

COMMAND_ENV_KEYS = {
    "gemma-4-e2b": "LOCAL_GEMMA_E2B_COMMAND",
    "gemma-4-e4b": "LOCAL_GEMMA_E4B_COMMAND",
}


@dataclass
class ModelResult:
    raw: str
    parsed: dict
    repair_notes: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0


def parse_model_response(raw_text):
    text = raw_text.strip()
    notes = []

    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
        notes.append("removed markdown code fence")

    try:
        return json.loads(text), notes
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            notes.append("extracted JSON object from surrounding text")
            return json.loads(text[start : end + 1]), notes
        raise


def _http_post_json(url, body, timeout_seconds):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LM Studio request failed: HTTP {exc.code}: {body_text}") from exc


def _model_id(model, env):
    env_key = MODEL_ENV_KEYS.get(model)
    if env_key and env.get(env_key):
        return env[env_key]
    return DEFAULT_MODEL_IDS.get(model, model)


class LmStudioRunner:
    name = "lmstudio"

    def __init__(
        self,
        model,
        base_url=None,
        timeout_seconds=None,
        temperature=0,
        post_json=None,
        env=None,
    ):
        self.env = env or os.environ
        self.model = model
        self.model_id = _model_id(model, self.env)
        self.base_url = (base_url or self.env.get("LMSTUDIO_BASE_URL") or "http://localhost:1234/v1").rstrip("/")
        self.timeout_seconds = int(timeout_seconds or self.env.get("LMSTUDIO_TIMEOUT_SECONDS") or 1200)
        self.temperature = temperature
        self.post_json = post_json or _http_post_json

    def run(self, source_type, prompt, response_format=None):
        body = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": response_format or response_format_for_source_type(source_type),
            "temperature": self.temperature,
            "stream": False,
        }
        start = time.perf_counter()
        response = self.post_json(
            f"{self.base_url}/chat/completions",
            body,
            self.timeout_seconds,
        )
        elapsed = time.perf_counter() - start

        choice = response["choices"][0]
        raw_content = choice["message"]["content"]
        parsed, repair_notes = parse_model_response(raw_content)
        diagnostics = {"finish_reason": choice.get("finish_reason")}
        total_tokens = response.get("usage", {}).get("total_tokens")
        if total_tokens is not None:
            diagnostics["total_tokens"] = total_tokens

        return ModelResult(
            raw=raw_content,
            parsed=parsed,
            repair_notes=repair_notes,
            diagnostics=diagnostics,
            elapsed_seconds=elapsed,
        )


class CommandRunner:
    name = "command"

    def __init__(self, model, command=None, timeout_seconds=1200, env=None):
        self.env = env or os.environ
        self.model = model
        self.command = command or self.env.get(COMMAND_ENV_KEYS.get(model, ""))
        self.timeout_seconds = timeout_seconds
        if not self.command:
            raise ValueError(f"No command configured for {model}")

    def run(self, source_type, prompt, response_format=None):
        start = time.perf_counter()
        completed = subprocess.run(
            self.command,
            input=prompt,
            shell=True,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        elapsed = time.perf_counter() - start
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"Command exited {completed.returncode}")

        parsed, repair_notes = parse_model_response(completed.stdout)
        return ModelResult(
            raw=completed.stdout,
            parsed=parsed,
            repair_notes=repair_notes,
            diagnostics={"returncode": completed.returncode},
            elapsed_seconds=elapsed,
        )


class FakeRunner:
    name = "fake"

    def run(self, source_type, prompt, response_format=None):
        parsed = blank_output_for_source_type(source_type)
        raw = json.dumps(parsed)
        return ModelResult(
            raw=raw,
            parsed=parsed,
            diagnostics={"fake": True},
            elapsed_seconds=0.0,
        )


class FakeAdvisoryRunner:
    name = "fake"

    def run(self, source_type, prompt, response_format=None):
        parsed = {}
        for field in schema_fields_for_source_type(source_type):
            parsed[f"{field}_status"] = "ok"
            parsed[f"{field}_suggested_value"] = ""
            parsed[f"{field}_reason"] = ""
        raw = json.dumps(parsed)
        return ModelResult(
            raw=raw,
            parsed=parsed,
            diagnostics={"fake": True},
            elapsed_seconds=0.0,
        )


class FakeRecoveryRunner:
    name = "fake"

    def run(self, source_type, prompt, response_format=None):
        fields = response_format["json_schema"]["schema"]["required"] if response_format else []
        parsed = {field: "" for field in fields}
        raw = json.dumps(parsed)
        return ModelResult(
            raw=raw,
            parsed=parsed,
            diagnostics={"fake": True},
            elapsed_seconds=0.0,
        )
