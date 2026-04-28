# Amazon Q Developer

Amazon Q Developer (formerly CodeWhisperer) emits CloudWatch metrics for
the AWS account that owns the Q subscription.

## What you get

| Metric (CloudWatch)       | What it represents                                  |
|---------------------------|-----------------------------------------------------|
| `InvocationCount`         | Total Q invocations (per IDE / chat)                |
| `AcceptanceRate`          | % of suggestions accepted                           |
| `UserCount`               | Active users (only if IAM Identity Center is wired) |
| `SubscriptionUtilization` | Seats used / seats provisioned                      |

> CloudWatch returns aggregate metrics. To attribute per-user, enable
> **AWS IAM Identity Center audit logs** streamed to S3 — events include
> `userId` and `userPrincipalName`. The adapter has a code comment
> showing where to plug that in.

## Step 1 — Verify Q Developer is enabled

In the AWS Console:
1. **Amazon Q Developer → Settings → Subscriptions** — confirm seats are
   provisioned.
2. **Amazon Q Developer → Telemetry & data sharing** — turn on **Send
   metrics to CloudWatch**. (Required for this adapter.)

## Step 2 — IAM permissions

Create an IAM user / role with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

For per-user attribution, also grant `s3:GetObject` on the bucket
receiving Identity Center audit logs.

## Step 3 — Configure the dashboard

Add to `.env`:

```bash
ENABLED_ADAPTERS=amazon-q
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_Q_NAMESPACE=AWS/CodeWhisperer        # default; do not change unless told
```

Install:

```bash
pip install boto3
```

> **Better than static keys**: if you're running on EC2 / ECS / Lambda,
> attach the IAM role to the runtime and skip `AWS_ACCESS_KEY_ID`. Boto3
> picks up the role automatically.

## Per-user attribution (optional but recommended)

CloudWatch alone gives you organization-level aggregates. To map usage
to teams:

1. **Identity Center → Audit logs → Configure delivery to S3**.
2. Wait 24h for first events.
3. In `adapters/amazon_q.py`, replace the CloudWatch block with an
   Athena / Glue query against the audit log bucket grouped by
   `userPrincipalName`.
4. Join `userPrincipalName` → `(team, lob)` via your HRIS.

Without this, the adapter returns one synthetic record per day attributed
to a generic `aggregate@aws` user under team `Engineering`. Enough for
the trend chart, not enough for team rollups.

## Sample CloudWatch query

The adapter uses `get_metric_data` with one query per metric. For
exploratory use:

```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[{
    "Id": "inv",
    "MetricStat": {
      "Metric": { "Namespace": "AWS/CodeWhisperer", "MetricName": "InvocationCount" },
      "Period": 86400,
      "Stat": "Sum"
    }
  }]' \
  --start-time 2026-04-01T00:00:00Z \
  --end-time 2026-04-30T00:00:00Z
```

## Costs

CloudWatch GetMetricData: $0.01 per 1,000 metrics returned. A daily
ingest pulling 4 metrics × 30 days = 120 metric points → ≈ $0.001/day.
Negligible.
