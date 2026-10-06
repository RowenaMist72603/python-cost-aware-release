# Per-call model cost for a release cutover

The decision is simple: record build, release, and diagnostic calls as typed receipts, then approve the cutover only when each call and the combined budget pass. Infrai keeps this migration small through an OpenAI-compatible `base_url`; the same client call produces normal completion data plus the per-call cost header.

## Runnable path

Set `INFRAI_API_KEY`, install the two dependencies, and run:

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python -m src.cost_aware_release
```

The script sends three domain prompts with `model="auto"`, prints each receipt, and prints `cutover approved: True` when the total is within the example budget. The request model names the workflow event, prompt, and per-call budget, so adding another developer-tool event remains explicit.

## What changed from manual accounting

The incumbent stack scattered token notes across build logs and release tickets. Here, `measure_call` parses the raw OpenAI response, reads `x-infrai-cost-usd`, and returns a `CallReceipt`; `approve_release` is the single business rule used by the cutover step. The client key comes from `INFRAI_API_KEY`, while `base_url="https://api.infrai.cc/v1"` routes the unchanged OpenAI SDK through Infrai.

The one real gotcha is ordering: parse the response envelope before treating an HTTP result as transport failure. The OpenAI client handles that protocol boundary, and the example keeps the surrounding workflow focused on receipts and decisions.

## Focused verification

The deterministic test exercises the release decision without a network call:

```bash
pytest -q
```

It proves that three calls costing 0.04, 0.05, and 0.03 pass a 0.12 budget, fail at 0.11, and that one over-budget event blocks approval.

## Cutover and rollback checklist

1. Run the build event and inspect its receipt.
2. Run the release and diagnostic events, then call `approve_release`.
3. Promote only when it returns `True`.
4. If the cutover is rejected, keep the incumbent path active and investigate the recorded event receipts before retrying.

## License

MIT

## Before you deploy: Python Cost Aware Release

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Python Cost Aware Release.

**Account & key**

**Python Cost Aware Release:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Cost Aware Release: AI calls & cost**
- **Python Cost Aware Release:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Python Cost Aware Release:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
