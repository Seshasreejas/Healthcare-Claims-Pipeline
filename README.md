# Healthcare Claims Pipeline

A small, real, testable version of the claims transformation logic used in
production Glue jobs this pipeline is modeled on: filter invalid records,
join against ICD/HCC reference data, filter to claims within a member's
active coverage window, and derive a risk score.

Built in pandas rather than PySpark specifically so it's lightweight to
run and unit test in CI without needing a live Spark cluster -- the same
filter/join/derive logic maps directly onto PySpark's `.filter()` /
`.join()` / `.withColumn()`.

## Pipeline steps

1. **Filter invalid claims** -- drop records missing required fields, or
   flagged `error` status.
2. **Join ICD -> HCC reference** -- attach `hcc_category` and `risk_weight`
   per diagnosis code.
3. **Filter to eligible claims** -- keep only claims whose `service_date`
   falls within that member's active coverage window. This mirrors the
   real eligibility-date-mismatch check behind the orphan-claims recovery
   process -- catching claims dated outside coverage before they reach
   output.
4. **Derive risk score** -- `billed_amount * risk_weight`.

## Run locally

```bash
pip install -r requirements.txt
python transform.py
```

Reads from `data/claims.csv`, `data/icd_hcc_mapping.csv`,
`data/membership.csv`; writes `data/output.csv`.

## Run tests

```bash
pytest tests/ -v
```

## CI/CD

`.github/workflows/ci.yml` runs on every push and PR against `main`:
lints with flake8, then runs the full test suite. A broken transformation
never merges silently.

## Infrastructure as Code

`terraform/main.tf` defines the real AWS pieces this would run on: an
encrypted S3 bucket, a least-privilege IAM role scoped to that bucket
only, and the Glue job itself -- pointing to the script's S3 location
rather than embedding the code, same separation of concerns as the
production pipeline.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## What this intentionally does NOT include

- No live AWS deployment in CI (would need real credentials/cost)
- No DynamoDB/Secrets Manager wiring (kept minimal for a from-scratch demo)
- Worker sizing (`G.1X`, 5 workers) is a light default for this small
  dataset, not a production sizing decision
