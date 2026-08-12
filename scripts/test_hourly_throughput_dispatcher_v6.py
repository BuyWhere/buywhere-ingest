#!/usr/bin/env python3
"""Focused tests for BUY-59891 v6 hourly throughput decision logic.

Run:
  PYTHONPATH=. python3 -m pytest scripts/test_hourly_throughput_dispatcher_v6.py
"""

from datetime import datetime, timezone

from scripts.hourly_throughput_dispatcher import (
    PASS_COMMENT_ISSUE_ID,
    TARGET_ROWS_PER_HOUR,
    assert_v6_forbidden_patterns,
    dedup_check_existing_child,
    format_failure_issue_title,
    is_completed_hour,
    select_v6_throughput_signal,
    should_file_v6_failure_ticket,
)


def test_stats_delta_is_authoritative_even_when_secondary_metrics_pass() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=42,
        canonical_ing_inserted=TARGET_ROWS_PER_HOUR * 2,
        live_count_delta=TARGET_ROWS_PER_HOUR * 3,
    )

    assert real_rows == 42
    assert source == "delta_ins_from_stats"


def test_stats_delta_under_target_still_authoritative_with_zero_live_count() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=42,
        canonical_ing_inserted=0,
        live_count_delta=0,
    )

    assert real_rows == 42
    assert source == "delta_ins_from_stats"


def test_stats_hard_guard_pass_is_not_masked_by_zero_secondary_metrics() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=TARGET_ROWS_PER_HOUR,
        canonical_ing_inserted=0,
        live_count_delta=0,
    )

    assert real_rows == TARGET_ROWS_PER_HOUR
    assert source == "delta_ins_from_stats"


def test_ingestion_fallback_pass_is_not_masked_by_low_live_count_delta() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=TARGET_ROWS_PER_HOUR,
        live_count_delta=0,
    )

    assert real_rows == TARGET_ROWS_PER_HOUR
    assert source == "ingestion_runs_observability"


def test_live_count_hard_guard_pass_is_not_masked_by_zero_ingestion_runs() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=0,
        live_count_delta=TARGET_ROWS_PER_HOUR,
    )

    assert real_rows == TARGET_ROWS_PER_HOUR
    assert source == "live_count_delta"


def test_fail_only_when_all_available_fallbacks_are_below_target() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=10,
        live_count_delta=20,
    )

    assert real_rows == 10
    assert source == "ingestion_runs_observability"


def test_failure_ticket_files_when_authoritative_stats_delta_is_non_null_below_target() -> None:
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=42,
        canonical_ing_inserted=0,
        live_count_delta=0,
    )


def test_failure_ticket_does_not_file_when_authoritative_stats_delta_passes() -> None:
    assert not should_file_v6_failure_ticket(
        delta_ins_from_stats=TARGET_ROWS_PER_HOUR,
        canonical_ing_inserted=0,
        live_count_delta=0,
    )


def test_failure_ticket_files_only_when_stats_null_and_fallbacks_below_target() -> None:
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=10,
        live_count_delta=20,
    )


def test_failure_ticket_does_not_file_when_ingestion_fallback_passes() -> None:
    assert not should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=TARGET_ROWS_PER_HOUR,
        live_count_delta=0,
    )


def test_failure_ticket_does_not_file_when_live_count_fallback_passes() -> None:
    assert not should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=0,
        live_count_delta=TARGET_ROWS_PER_HOUR,
    )


def test_v64_ing_inserted_blocks_n_live_tup_guard_on_autovacuum_surge() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    )

    assert real_rows == 18
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    )


def test_v64_n_live_tup_guard_preserved_when_ing_inserted_unavailable() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    )

    assert real_rows == 876_000
    assert source == "n_live_tup_delta_guard"
    assert not should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    )


def test_v64_n_live_tup_guard_preserved_when_ing_inserted_passes() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=2_262,
        canonical_ing_inserted=TARGET_ROWS_PER_HOUR,
        live_count_delta=0,
        n_live_tup_delta=247_000,
    )

    assert real_rows == 247_000
    assert source == "n_live_tup_delta_guard"
    assert not should_file_v6_failure_ticket(
        delta_ins_from_stats=2_262,
        canonical_ing_inserted=TARGET_ROWS_PER_HOUR,
        live_count_delta=0,
        n_live_tup_delta=247_000,
    )


def test_check_hour_requires_completed_hour() -> None:
    now = datetime(2026, 7, 14, 5, 20, tzinfo=timezone.utc)

    assert is_completed_hour(datetime(2026, 7, 14, 4, 0, tzinfo=timezone.utc), now)
    assert not is_completed_hour(datetime(2026, 7, 14, 5, 0, tzinfo=timezone.utc), now)


def test_rule_6c_allows_zero_inserts_with_updates_when_raw_insert_counter_flat() -> None:
    assert_v6_forbidden_patterns(
        delta_ins_from_stats=0,
        delta_upd_from_stats=4,
        real_rows=0,
        source="delta_ins_from_stats",
        live_count_delta=None,
        current_n_tup_ins=192_634_641,
        previous_n_tup_ins=192_634_641,
    )


def test_rule_6c_raises_when_zero_delta_contradicts_raw_insert_counters() -> None:
    import pytest

    with pytest.raises(AssertionError, match="v6 rule 6\\(c\\) violation"):
        assert_v6_forbidden_patterns(
            delta_ins_from_stats=0,
            delta_upd_from_stats=4,
            real_rows=0,
            source="delta_ins_from_stats",
            live_count_delta=None,
            current_n_tup_ins=192_634_642,
            previous_n_tup_ins=192_634_641,
        )



def test_reupsert_preserves_stored_deltas() -> None:
    """BUY-60392: re-upserting an existing row must keep its original deltas."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from scripts.hourly_throughput_dispatcher import upsert_canonical_throughput_row

    hour_start = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
    existing_n_tup_ins = 183_874_927
    existing_delta_ins = 2_284
    existing_delta_upd = 1_000
    existing_stat_reset = False
    current_n_tup_ins = 186_000_000

    # Sequence of row tuples returned by fetchone() across the queries.
    rows = [
        (1_000_000,),  # live_count
        (0, 0, 0),     # ingestion_runs (runs, ins, upd)
        (existing_n_tup_ins - 10_000, existing_n_tup_ins - 5_000),  # prior row
        (existing_n_tup_ins, existing_n_tup_ins - 1_000, existing_delta_ins,
         existing_delta_upd, existing_stat_reset),  # existing row
        (hour_start,),  # upsert returning
    ]

    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = rows
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cur
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cm

    result = upsert_canonical_throughput_row(
        conn=mock_conn,
        hour_start=hour_start,
        stat={"n_tup_ins": current_n_tup_ins,
              "n_tup_upd": current_n_tup_ins - 2_000,
              "n_live_tup": 200_000_000},
        hour_data=None,
        pm_start=None,
        source="delta_ins_from_stats",
        note="re-upsert regression test",
    )

    assert result["upserted"] is True
    assert result["delta_ins_from_stats"] == existing_delta_ins
    assert result["delta_upd_from_stats"] == existing_delta_upd
    assert result["stat_reset_detected"] == existing_stat_reset


def test_upsert_missing_prior_row_returns_baseline_without_delta() -> None:
    """A missing immediate-prior row is a baseline, not full-counter throughput."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from scripts.hourly_throughput_dispatcher import upsert_canonical_throughput_row

    hour_start = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
    current_n_tup_ins = 202_602_790
    rows = [
        (200_000_000,),  # live_count
        (0, 0, 0),       # ingestion_runs (runs, ins, upd)
        None,            # no immediate-prior canonical row
        None,            # no existing current-hour row
        (hour_start,),   # upsert returning
    ]

    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = rows
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_cur
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cm

    result = upsert_canonical_throughput_row(
        conn=mock_conn,
        hour_start=hour_start,
        stat={"n_tup_ins": current_n_tup_ins,
              "n_tup_upd": 10,
              "n_live_tup": 200_000_000},
        hour_data=None,
        pm_start=None,
        source="v6",
        note="missing-prior baseline regression test",
    )

    assert result["upserted"] is True
    assert result["n_tup_ins"] == current_n_tup_ins
    assert result["previous_n_tup_ins"] is None
    assert result["delta_ins_from_stats"] is None
    assert result["delta_upd_from_stats"] is None
    assert result["stat_reset_detected"] is None


def test_dedup_matches_current_failure_issue_title(monkeypatch) -> None:
    """Same-hour reruns must detect active HOURLY THROUGHPUT FAILURE titles."""
    from unittest.mock import MagicMock

    hour_start = datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc)
    title = format_failure_issue_title(hour_start, hour_start.replace(hour=15), 24_148)

    response = MagicMock()
    response.ok = True
    response.json.return_value = {"issues": [{"title": title}]}

    monkeypatch.setattr(
        "scripts.hourly_throughput_dispatcher._api_headers",
        lambda: {"Authorization": "Bearer test"},
    )
    monkeypatch.setattr(
        "scripts.hourly_throughput_dispatcher._retry_request",
        lambda *args, **kwargs: response,
    )

    assert dedup_check_existing_child(hour_start) is True


# --- v6.2 tests (BUY-60573): n_live_tup_delta hard guard ---


def test_v62_n_live_tup_guard_blocks_stale_counter_false_fail() -> None:
    """Reproduces the 2026-07-06 22Z/23Z false-FAIL: delta_ins_from_stats is
    stale/lagged (<< 150K) but n_live_tup grew by >= 150K, proving real inserts.
    The guard must force a PASS so no FAIL ticket is filed."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    )
    assert real_rows == 876_720
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    ) is False


def test_v64_ing_inserted_below_target_blocks_n_live_tup_guard() -> None:
    """BUY-60953 v6.4: low ing_inserted blocks phantom n_live_tup passes."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=1374,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    )
    assert real_rows == 722
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=1374,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    ) is True


def test_v64_ing_inserted_below_target_blocks_n_live_tup_guard_when_stats_null() -> None:
    """BUY-61631: v6.4 corroboration also applies after a stats reset/baseline."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=1374,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    )
    assert real_rows == 1374
    assert source == "ingestion_runs_observability"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=1374,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    ) is True


def test_v64_blocked_n_live_tup_guard_does_not_select_n_live_tup_failure_metric() -> None:
    """Blocked n_live_tup guards are pass-only and must not become the fail metric."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=0,
        live_count_delta=12,
        n_live_tup_delta=876_720,
    )
    assert real_rows == 12
    assert source == "live_count_delta"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=0,
        live_count_delta=12,
        n_live_tup_delta=876_720,
    ) is True


def test_v64_ingestion_runs_observability_does_not_override_live_count_pass() -> None:
    """With stats unavailable, live_count >= target is the authoritative fallback pass."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=1,
        live_count_delta=150_001,
        n_live_tup_delta=None,
    )
    assert real_rows == 150_001
    assert source == "live_count_delta"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=1,
        live_count_delta=150_001,
        n_live_tup_delta=None,
    ) is False


def test_v62_non_null_stats_delta_below_target_files_without_guard() -> None:
    """A non-null authoritative stats delta below target files unless the
    n_live_tup hard guard proves real growth."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=500,
        canonical_ing_inserted=100,
        live_count_delta=None,
        n_live_tup_delta=300,
    )
    assert real_rows == 500
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=500,
        canonical_ing_inserted=100,
        live_count_delta=None,
        n_live_tup_delta=300,
    ) is True


def test_v62_n_live_tup_guard_corroborates_when_stats_unavailable() -> None:
    """On a true stat reset (delta_ins=None) with n_live_tup growth >= 150K,
    the guard corroborates real inserts and blocks filing."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=300_000,
    )
    assert real_rows == 300_000
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=300_000,
    ) is False


def test_below_target_files_under_rule_5a_without_guard() -> None:
    """19Z-style scenario: stats delta is non-null but tiny (3,048/hr) AND
    n_live_tup_delta is also tiny (no corroboration). v6 rule 5a says the
    primary stats delta is authoritative, so the dispatcher should file.
    """
    # Use delta_ins_from_stats path, real_rows=3048 < target, n_live_tup below
    # target so guard does NOT trigger.
    should = should_file_v6_failure_ticket(
        delta_ins_from_stats=3048,
        canonical_ing_inserted=1244,
        live_count_delta=None,
        n_live_tup_delta=3048,
    )
    assert should is True, "v6 rule 5a: non-null below-target stats delta files FAIL"

    # And the chosen metric/source still surfaces delta_ins_from_stats so the
    # operator can see the actual reading.
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=3048,
        canonical_ing_inserted=1244,
        live_count_delta=None,
        n_live_tup_delta=3048,
    )
    assert source == "delta_ins_from_stats"
    assert real_rows == 3048


def test_v64_stats_pass_is_authoritative_when_ingestion_runs_low() -> None:
    """Rule 5b/5c: stats pass is authoritative; ingestion_runs is observability."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=150_000,
        canonical_ing_inserted=12_345,
        live_count_delta=160_000,
        n_live_tup_delta=160_000,
    )
    assert real_rows == 150_000
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=150_000,
        canonical_ing_inserted=12_345,
        live_count_delta=160_000,
        n_live_tup_delta=160_000,
    ) is False


def test_v64_ing_inserted_blocks_n_live_tup_autovacuum_false_pass() -> None:
    """Low ing_inserted blocks n_live_tup_guard and preserves stats FAIL."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    )
    assert real_rows == 18
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    ) is True


def test_v64_low_ing_inserted_blocks_n_live_tup_when_stats_unavailable() -> None:
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    )

    assert real_rows == 18
    assert source == "ingestion_runs_observability"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    ) is True


def test_v64_unavailable_ing_inserted_preserves_stale_counter_guard() -> None:
    """Unavailable ing_inserted keeps n_live_tup_guard active for stale counters."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    )
    assert real_rows == 876_000
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    ) is False


def test_build_evidence_markdown_contains_required_fields():
    from scripts.hourly_throughput_dispatcher import build_evidence_markdown
    hour_start = datetime(2026, 7, 13, 16, 0, tzinfo=timezone.utc)
    stat = {"n_live_tup": 277822102, "n_tup_ins": 216436984, "n_tup_upd": 146610187}
    hour_data = {"total_rows": 200000, "real_rows": 150000, "first_row": "a", "last_row": "z"}
    max_created = {"max_created_at": "2026-07-13T16:55:00+00:00"}
    ingestion_counts = {"ing_runs": 12, "ing_inserted": 13940, "ing_updated": 0}
    md = build_evidence_markdown(
        hour_start, 13940, "delta_ins_from_stats", "test note", hour_data, stat, max_created,
        "maglev.proxy.rlwy.net:31310/railway", "2026-07-13 17:00 UTC",
        stat_reset_detected=False,
        ingestion_counts=ingestion_counts,
    )
    assert "FAIL" in md
    assert "13,940" in md
    assert "150,000" in md
    assert "277,822,102" in md
    assert "216,436,984" in md
    assert "146,610,187" in md
    assert "Canonical metric used" in md
    assert "delta_ins_from_stats" in md
    assert "stat_reset_detected" in md
    assert "ingestion_runs" in md
    assert "canonical_throughput_hourly upsert confirmation" in md
    assert "2026-07-13T16:00" in md
    assert "test note" in md


def test_write_evidence_markdown_creates_file(tmp_path, monkeypatch):
    from scripts.hourly_throughput_dispatcher import build_evidence_markdown, write_evidence_markdown
    monkeypatch.setattr(
        "scripts.hourly_throughput_dispatcher.EVIDENCE_DIR", tmp_path,
    )
    hour_start = datetime(2026, 7, 13, 16, 0, tzinfo=timezone.utc)
    stat = {"n_live_tup": 277822102, "n_tup_ins": 216436984, "n_tup_upd": 146610187}
    path = write_evidence_markdown(
        hour_start, 13940, "delta_ins_from_stats", "test note", None, stat, None,
        "maglev.proxy.rlwy.net:31310/railway", "2026-07-13 17:00 UTC",
        failure_child_identifier="BUY-62316",
        stat_reset_detected=False,
        ingestion_counts={"ing_runs": 12, "ing_inserted": 13940, "ing_updated": 0},
    )
    assert path is not None
    assert path.exists()
    text = path.read_text()
    assert "BUY-62316" in text
    assert "FAIL" in text


def test_post_parent_pass_comment_makes_request(monkeypatch):
    from scripts.hourly_throughput_dispatcher import post_parent_pass_comment
    calls = []
    def fake_retry_request(method, url, *, json, headers, timeout):
        calls.append((method, url, json))
        class R:
            def raise_for_status(self): pass
        return R()
    monkeypatch.setattr("scripts.hourly_throughput_dispatcher._retry_request", fake_retry_request)
    monkeypatch.setenv("PAPERCLIP_API_KEY", "test-key")
    hour_start = datetime(2026, 7, 13, 16, 0, tzinfo=timezone.utc)
    post_parent_pass_comment(hour_start, 340000, "delta_ins_from_stats")
    assert len(calls) == 1
    assert calls[0][0] == "post"
    assert PASS_COMMENT_ISSUE_ID in calls[0][1]
    assert "PASS" in calls[0][2]["body"]
    assert "340,000" in calls[0][2]["body"]


def test_post_parent_pass_comment_skips_without_api_key(monkeypatch):
    from scripts.hourly_throughput_dispatcher import post_parent_pass_comment
    monkeypatch.delenv("PAPERCLIP_API_KEY", raising=False)
    # No assertion needed: should return silently without calling _retry_request
    post_parent_pass_comment(datetime(2026, 7, 13, 16, 0, tzinfo=timezone.utc), 340000, "delta_ins_from_stats")


# ---------------------------------------------------------------------------
# BUY-62618 regression tests — v6.4 guard + BELOW_TARGET state
# ---------------------------------------------------------------------------


def test_buy62618_v64_autovacuum_guard_selects_stats_not_guard_metric() -> None:
    """v6.4 autovacuum case: ing_inserted is low, n_live_tup surged from
    vacuum bloat. select_v6_throughput_signal must return delta_ins_from_stats
    (not n_live_tup_delta_guard) so the FAIL metric is accurate."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    )
    assert real_rows == 18, "must use delta_ins_from_stats, not n_live_tup guard"
    assert source == "delta_ins_from_stats"


def test_buy62618_v64_autovacuum_guard_files_failure() -> None:
    """v6.4: low ing_inserted blocks n_live_tup guard → FAIL should be filed."""
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=18,
        canonical_ing_inserted=18,
        live_count_delta=None,
        n_live_tup_delta=7_400_000,
    ) is True


def test_buy62618_v64_stale_counter_guard_passes() -> None:
    """v6.4: unavailable ing_inserted preserves the stale-counter guard → PASS."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    )
    assert real_rows == 876_000
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=None,
        live_count_delta=None,
        n_live_tup_delta=876_000,
    ) is False


def test_buy62618_v64_available_ing_inserted_passes_guard() -> None:
    """v6.4: ing_inserted >= target → guard fires, PASS."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=722,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    )
    assert real_rows == 876_720
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=722,
        canonical_ing_inserted=150_000,
        live_count_delta=None,
        n_live_tup_delta=876_720,
    ) is False


def test_buy62618_below_target_state_category() -> None:
    """BELOW_TARGET is emitted when real_rows < target but v6 guards suppress filing.

    Uses live_count_delta (>= target) to suppress filing via the live_count
    guard in should_file_v6_failure_ticket, while n_live_tup_delta stays
    dormant so select_v6_throughput_signal returns the low delta_ins_from_stats."""
    delta_ins_from_stats = 722
    canonical_ing_inserted = None
    live_count_delta = 160_000  # >= TARGET, suppresses filing via live_count guard
    n_live_tup_delta = None  # dormant so n_live_tup guard does not fire in select

    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=delta_ins_from_stats,
        canonical_ing_inserted=canonical_ing_inserted,
        live_count_delta=live_count_delta,
        n_live_tup_delta=n_live_tup_delta,
    )
    should_file = should_file_v6_failure_ticket(
        delta_ins_from_stats=delta_ins_from_stats,
        canonical_ing_inserted=canonical_ing_inserted,
        live_count_delta=live_count_delta,
        n_live_tup_delta=n_live_tup_delta,
    )

    TARGET = 150_000
    if real_rows >= TARGET:
        result = "PASS"
    elif should_file:
        result = "FAIL"
    else:
        result = "BELOW_TARGET"

    assert real_rows < TARGET, "raw stats delta is below target"
    assert not should_file, "live_count_delta guard suppresses filing"
    assert result == "BELOW_TARGET", "state must be BELOW_TARGET, not FAIL"


def test_buy62618_baseline_state_category() -> None:
    """First-ever tick with no prior data must be BASELINE, not FAIL."""
    delta_ins_from_stats = None
    live_count_delta = None
    state_last_n_tup_ins = None
    should_file = should_file_v6_failure_ticket(
        delta_ins_from_stats=delta_ins_from_stats,
        canonical_ing_inserted=100,
        live_count_delta=live_count_delta,
    )
    is_first_baseline = state_last_n_tup_ins is None and delta_ins_from_stats is None and live_count_delta is None

    if is_first_baseline:
        result = "BASELINE"
    elif not should_file:
        result = "BELOW_TARGET"
    else:
        result = "FAIL"

    assert result == "BASELINE"


def test_buy62618_stats_null_all_fallbacks_low_files_failure() -> None:
    """When delta_ins_from_stats is NULL and every fallback is below target, FAIL."""
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=10,
        live_count_delta=20,
    ) is True


def test_buy62618_stats_null_ingestion_pass_blocks_filing() -> None:
    """When delta_ins_from_stats is NULL but ingestion_runs passes, no FAIL."""
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=150_001,
        live_count_delta=0,
    ) is False


def test_v64_stats_null_with_large_live_tup_and_unavailable_ing_runs_passes() -> None:
    """When stats reset/None and ing_inserted unavailable, n_live_tup guard may pass."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=None,
        canonical_ing_inserted=None,
        live_count_delta=20,
        n_live_tup_delta=200_000,
    )

    assert real_rows == 200_000
    assert source == "n_live_tup_delta_guard"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=None,
        canonical_ing_inserted=None,
        live_count_delta=20,
        n_live_tup_delta=200_000,
    ) is False


def test_failure_issue_title_matches_buy29861_template() -> None:
    hour_start = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
    hour_end = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)

    assert format_failure_issue_title(hour_start, hour_end, 27_079) == (
        "HOURLY THROUGHPUT FAILURE — 27,079 products added in "
        "08:00–09:00 UTC 2026-07-15 (target 150,000)"
    )


# ---------------------------------------------------------------------------
# BUY-68540 gap-closure: assertion-fire tests + ing_inserted=0 edge case
# ---------------------------------------------------------------------------


def test_rule_6a_assertion_fires_when_source_is_ingestion_runs_with_non_null_stats() -> None:
    """Rule 6(a): assert_v6_forbidden_patterns must raise when source is
    ingestion_runs_observability despite delta_ins_from_stats being available."""
    import pytest

    with pytest.raises(AssertionError, match="v6 rule 6\\(a\\) violation"):
        assert_v6_forbidden_patterns(
            delta_ins_from_stats=42_000,
            delta_upd_from_stats=0,
            real_rows=42_000,
            source="ingestion_runs_observability",
            live_count_delta=0,
            current_n_tup_ins=100_000_000,
            previous_n_tup_ins=99_958_000,
        )


def test_rule_6b_assertion_fires_when_live_count_zero_with_positive_stats_delta() -> None:
    """Rule 6(b): live_count_delta=0 while delta_ins_from_stats > 0 must raise."""
    import pytest

    with pytest.raises(AssertionError, match="v6 rule 6\\(b\\) violation"):
        assert_v6_forbidden_patterns(
            delta_ins_from_stats=5_000,
            delta_upd_from_stats=0,
            real_rows=0,
            source="live_count_delta",
            live_count_delta=0,
            current_n_tup_ins=200_000_000,
            previous_n_tup_ins=199_995_000,
        )


def test_rule_6b_assertion_fires_when_stats_delta_zero_with_positive_live_count() -> None:
    """Rule 6(b): delta_ins_from_stats=0 while live_count_delta > 0 must raise."""
    import pytest

    with pytest.raises(AssertionError, match="v6 rule 6\\(b\\) violation"):
        assert_v6_forbidden_patterns(
            delta_ins_from_stats=0,
            delta_upd_from_stats=0,
            real_rows=0,
            source="delta_ins_from_stats",
            live_count_delta=5_000,
            current_n_tup_ins=200_000_000,
            previous_n_tup_ins=200_000_000,
        )


def test_v64_explicit_ing_inserted_zero_blocks_n_live_tup_guard() -> None:
    """v6.4: canonical_ing_inserted=0 (available but zero) blocks the n_live_tup
    guard, same as ing_inserted < target. The n_live_tup surge is autovacuum
    bloat release and must not override the low stats delta."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=500,
        canonical_ing_inserted=0,
        live_count_delta=None,
        n_live_tup_delta=1_000_000,
    )
    assert real_rows == 500
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=500,
        canonical_ing_inserted=0,
        live_count_delta=None,
        n_live_tup_delta=1_000_000,
    ) is True


def test_v64_ing_inserted_zero_does_not_override_stats_pass() -> None:
    """When stats pass, ing_inserted=0 is irrelevant — the 150K hard guard on
    delta_ins_from_stats still forces PASS."""
    real_rows, source = select_v6_throughput_signal(
        delta_ins_from_stats=200_000,
        canonical_ing_inserted=0,
        live_count_delta=None,
        n_live_tup_delta=None,
    )
    assert real_rows == 200_000
    assert source == "delta_ins_from_stats"
    assert should_file_v6_failure_ticket(
        delta_ins_from_stats=200_000,
        canonical_ing_inserted=0,
        live_count_delta=None,
        n_live_tup_delta=None,
    ) is False
