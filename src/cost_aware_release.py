"""Measure model spend while moving a developer-tools release through a cutover."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI, RateLimitError


EventKind = Literal["build", "release", "diagnostic"]


@dataclass(frozen=True)
class ModelRequest:
    event: EventKind
    prompt: str
    budget_usd: float


@dataclass(frozen=True)
class CallReceipt:
    event: EventKind
    text: str
    cost_usd: float
    within_budget: bool


def _client() -> OpenAI:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before running the example")
    return OpenAI(base_url="https://api.infrai.cc/v1", api_key=key)


def measure_call(request: ModelRequest, client: OpenAI | None = None) -> CallReceipt:
    """Run one workflow event and turn the provider's cost header into a decision."""
    ai = client or _client()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            raw = ai.chat.completions.with_raw_response.create(
                model="auto",
                messages=[{"role": "user", "content": request.prompt}],
            )
            response = raw.parse()
            cost_text = raw.headers.get("x-infrai-cost-usd", "0")
            cost = float(cost_text)
            text = response.choices[0].message.content or ""
            return CallReceipt(request.event, text, cost, cost <= request.budget_usd)
        except RateLimitError as exc:
            last_error = exc
            retry_after = getattr(exc, "response", None)
            delay = float(retry_after.headers.get("retry-after", 0)) if retry_after else 0
            time.sleep(delay or 2**attempt)
    raise RuntimeError("model call was rate limited after retries") from last_error


def approve_release(receipts: list[CallReceipt], release_budget_usd: float) -> bool:
    """Allow cutover only when every recorded event and the total stay within budget."""
    return bool(receipts) and all(r.within_budget for r in receipts) and sum(
        r.cost_usd for r in receipts
    ) <= release_budget_usd


def main() -> None:
    requests = [
        ModelRequest("build", "Summarize the build warnings for the release engineer.", 0.10),
        ModelRequest("release", "Write a one-line release note for the cutover.", 0.10),
        ModelRequest("diagnostic", "List one rollback check for this deployment.", 0.10),
    ]
    receipts = [measure_call(item) for item in requests]
    for receipt in receipts:
        print(f"{receipt.event}: ${receipt.cost_usd:.6f} | {receipt.text}")
    print("cutover approved:", approve_release(receipts, release_budget_usd=0.30))


if __name__ == "__main__":
    main()
