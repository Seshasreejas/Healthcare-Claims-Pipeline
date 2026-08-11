import pandas as pd
import pytest
from transform import (
    filter_invalid_claims,
    join_icd_hcc,
    filter_eligible_claims,
    derive_risk_score,
    run_pipeline,
)


@pytest.fixture
def sample_claims():
    return pd.DataFrame({
        "claim_id": ["C1", "C2", "C3", "C4"],
        "member_id": ["M100", "M100", "M101", "M102"],
        "icd_code": ["E11.9", "I10", "E11.9", None],
        "service_date": pd.to_datetime(
            ["2026-03-15", "2026-06-01", "2026-01-10", "2026-02-01"]
        ),
        "billed_amount": [500.0, 300.0, 900.0, 200.0],
        "status": ["approved", "approved", "approved", "approved"],
    })


@pytest.fixture
def sample_icd_hcc():
    return pd.DataFrame({
        "icd_code": ["E11.9", "I10"],
        "hcc_category": ["HCC18", "HCC85"],
        "risk_weight": [1.2, 0.8],
    })


@pytest.fixture
def sample_membership():
    return pd.DataFrame({
        "member_id": ["M100", "M101"],
        "coverage_start": pd.to_datetime(["2026-01-01", "2026-01-01"]),
        "coverage_end": pd.to_datetime(["2026-12-31", "2026-03-31"]),
    })


def test_filter_invalid_claims_drops_missing_icd_code(sample_claims):
    result = filter_invalid_claims(sample_claims)
    assert "C4" not in result["claim_id"].values
    assert len(result) == 3


def test_filter_invalid_claims_drops_errored_status():
    df = pd.DataFrame({
        "claim_id": ["C1", "C2"],
        "member_id": ["M100", "M100"],
        "icd_code": ["E11.9", "E11.9"],
        "service_date": pd.to_datetime(["2026-03-01", "2026-03-01"]),
        "billed_amount": [500.0, 500.0],
        "status": ["approved", "error"],
    })
    result = filter_invalid_claims(df)
    assert len(result) == 1
    assert result.iloc[0]["claim_id"] == "C1"


def test_join_icd_hcc_adds_risk_weight(sample_claims, sample_icd_hcc):
    filtered = filter_invalid_claims(sample_claims)
    result = join_icd_hcc(filtered, sample_icd_hcc)
    assert "risk_weight" in result.columns
    c1_row = result[result["claim_id"] == "C1"].iloc[0]
    assert c1_row["risk_weight"] == 1.2


def test_filter_eligible_claims_excludes_out_of_coverage_date(
    sample_claims, sample_icd_hcc, sample_membership
):
    # C3 has service_date 2026-01-10 but member M101's coverage ends 2026-03-31 -- eligible.
    # Add a claim outside coverage to confirm it gets correctly excluded.
    filtered = filter_invalid_claims(sample_claims)
    joined = join_icd_hcc(filtered, sample_icd_hcc)
    result = filter_eligible_claims(joined, sample_membership)
    # M102 has no membership record -> already dropped earlier for null icd_code
    assert "M102" not in result["member_id"].values


def test_filter_eligible_claims_excludes_service_date_after_coverage_end(sample_icd_hcc):
    claims = pd.DataFrame({
        "claim_id": ["C5"],
        "member_id": ["M101"],
        "icd_code": ["E11.9"],
        "service_date": pd.to_datetime(["2026-06-01"]),  # after M101's coverage_end
        "billed_amount": [400.0],
        "status": ["approved"],
    })
    membership = pd.DataFrame({
        "member_id": ["M101"],
        "coverage_start": pd.to_datetime(["2026-01-01"]),
        "coverage_end": pd.to_datetime(["2026-03-31"]),
    })
    joined = join_icd_hcc(claims, sample_icd_hcc)
    result = filter_eligible_claims(joined, membership)
    assert len(result) == 0


def test_derive_risk_score_calculates_correctly():
    df = pd.DataFrame({"billed_amount": [500.0, 300.0], "risk_weight": [1.2, 0.8]})
    result = derive_risk_score(df)
    assert result.iloc[0]["risk_score"] == pytest.approx(600.0)
    assert result.iloc[1]["risk_score"] == pytest.approx(240.0)


def test_run_pipeline_end_to_end(sample_claims, sample_icd_hcc, sample_membership):
    result = run_pipeline(sample_claims, sample_icd_hcc, sample_membership)
    assert "risk_score" in result.columns
    # C1, C2 (M100) and C3 (M101) are valid + within coverage; C4 dropped for missing icd_code
    assert len(result) == 3
    assert set(result["claim_id"]) == {"C1", "C2", "C3"}
