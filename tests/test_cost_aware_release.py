from src.cost_aware_release import CallReceipt, approve_release


def test_cutover_requires_each_event_and_total_budget() -> None:
    receipts = [
        CallReceipt("build", "ok", 0.04, True),
        CallReceipt("release", "ok", 0.05, True),
        CallReceipt("diagnostic", "ok", 0.03, True),
    ]
    assert approve_release(receipts, 0.12)
    assert not approve_release(receipts, 0.11)
    assert not approve_release([CallReceipt("release", "ok", 0.01, False)], 0.12)
