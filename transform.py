"""
Claims transformation pipeline.

Mirrors the real Glue/PySpark job logic (filter -> join against membership
-> join against ICD/HCC reference -> derive risk score) implemented in
pandas here so it's lightweight to unit test in CI. The same functions
translate directly to PySpark: pandas DataFrame filtering/joins map to
.filter()/.join() on a Spark DataFrame with the same logic.
"""

import pandas as pd


def filter_invalid_claims(claims_df: pd.DataFrame) -> pd.DataFrame:
    """Drop claims that are errored or missing required fields."""
    required = ["claim_id", "member_id", "icd_code", "service_date", "billed_amount"]
    df = claims_df.dropna(subset=required)
    df = df[df["status"] != "error"]
    return df.reset_index(drop=True)


def join_icd_hcc(claims_df: pd.DataFrame, icd_hcc_ref: pd.DataFrame) -> pd.DataFrame:
    """Join claims against the ICD -> HCC category / risk weight reference table."""
    return claims_df.merge(icd_hcc_ref, on="icd_code", how="left")


def filter_eligible_claims(claims_df: pd.DataFrame, membership_ref: pd.DataFrame) -> pd.DataFrame:
    """
    Join against membership and keep only claims where the service date
    falls within that member's active coverage window. This mirrors the
    real eligibility-date-mismatch check (the root cause behind the
    orphan-claims story) -- catching claims dated outside coverage.
    """
    merged = claims_df.merge(membership_ref, on="member_id", how="left")
    eligible = merged[
        (merged["service_date"] >= merged["coverage_start"])
        & (merged["service_date"] <= merged["coverage_end"])
    ]
    return eligible.reset_index(drop=True)


def derive_risk_score(claims_df: pd.DataFrame) -> pd.DataFrame:
    """Derived column: billed_amount weighted by the HCC risk_weight."""
    df = claims_df.copy()
    df["risk_score"] = df["billed_amount"] * df["risk_weight"]
    return df


def run_pipeline(
    claims_df: pd.DataFrame,
    icd_hcc_ref: pd.DataFrame,
    membership_ref: pd.DataFrame,
) -> pd.DataFrame:
    """Full transformation: filter -> join ICD/HCC -> filter eligible -> derive risk score."""
    df = filter_invalid_claims(claims_df)
    df = join_icd_hcc(df, icd_hcc_ref)
    df = filter_eligible_claims(df, membership_ref)
    df = derive_risk_score(df)
    return df


if __name__ == "__main__":
    claims = pd.read_csv("data/claims.csv", parse_dates=["service_date"])
    icd_hcc = pd.read_csv("data/icd_hcc_mapping.csv")
    membership = pd.read_csv(
        "data/membership.csv",
        parse_dates=["coverage_start", "coverage_end"],
    )
    result = run_pipeline(claims, icd_hcc, membership)
    result.to_csv("data/output.csv", index=False)
    print(f"Processed {len(result)} eligible claims.")
