\# Healthcare Claims Data Pipeline on AWS



End-to-end data pipeline for processing healthcare claims using AWS cloud services.



\## Architecture

Raw Claims (CSV) → S3 → Lambda → Step Functions → Glue (PySpark) → Iceberg Tables → Redshift



\## Tech Stack

\- Storage: AWS S3, Apache Iceberg

\- Processing: AWS Glue, PySpark

\- Orchestration: AWS Lambda, Step Functions

\- Warehouse: Amazon Redshift

\- Governance: AWS Lake Formation, IAM

\- Infrastructure: Terraform, GitHub Actions (CI/CD)



\## Project Status

🔨 In progress — 30-day build



\## Folder Structure

\- /data — sample claims data

\- /glue\_jobs — PySpark ETL scripts

\- /lambda — Lambda trigger functions

\- /step\_functions — state machine definitions

\- /terraform — infrastructure as code

