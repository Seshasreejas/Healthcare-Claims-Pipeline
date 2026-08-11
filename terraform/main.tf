# Minimal IaC mirroring the pipeline built by hand in the AWS console this week.
# Terraform manages the Glue job's CONFIGURATION -- it points to the script's
# S3 location, it does not contain the transformation code itself. The
# actual transform.py gets uploaded to S3 separately (e.g. by the CI/CD
# pipeline), and this config just tells Glue where to find it.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Bucket holding raw claims, reference data, and the Glue script itself
resource "aws_s3_bucket" "claims_bucket" {
  bucket = "claims-pipeline-demo"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "claims_bucket_encryption" {
  bucket = aws_s3_bucket.claims_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# IAM role Glue assumes to run the job -- least-privilege, scoped to this bucket only
resource "aws_iam_role" "glue_role" {
  name = "claims-glue-job-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "glue-s3-access"
  role = aws_iam_role.glue_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.claims_bucket.arn,
        "${aws_s3_bucket.claims_bucket.arn}/*"
      ]
    }]
  })
}

# The Glue job itself -- points to the script location in S3, doesn't embed the code.
# G.1X / 5 workers is a light default for this small demo; real sizing
# depends on actual data volume, same DPU reasoning as the production job.
resource "aws_glue_job" "claims_transform_job" {
  name     = "claims-transform-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.claims_bucket.bucket}/scripts/transform.py"
    python_version  = "3"
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 5
}

output "bucket_name" {
  value = aws_s3_bucket.claims_bucket.bucket
}

output "glue_job_name" {
  value = aws_glue_job.claims_transform_job.name
}
