"""
Amazon Q Developer adapter.

Amazon Q Developer usage is exposed through CloudWatch metrics emitted
by the AWS account that owns the Q subscription. See:
    docs/data-sources/amazon-q.md

Required env vars:
    AWS_REGION             - e.g. us-east-1
    AWS_ACCESS_KEY_ID      - or use IAM role / SSO
    AWS_SECRET_ACCESS_KEY  - same
    AWS_Q_NAMESPACE        - default: AWS/CodeWhisperer
"""
from __future__ import annotations

import os
from datetime import date, datetime, time

from .base import Adapter, AdapterMeta, UsageRecord


class AmazonQAdapter(Adapter):
    meta = AdapterMeta(
        id="amazon-q",
        name="Amazon Q Developer",
        vendor="AWS",
        color="#f59e0b",
        cost_per_1k_tokens=0.014,
    )

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        """
        Production implementation outline:

            import boto3
            cw = boto3.client("cloudwatch", region_name=os.environ["AWS_REGION"])
            namespace = os.getenv("AWS_Q_NAMESPACE", "AWS/CodeWhisperer")

            response = cw.get_metric_data(
                MetricDataQueries=[{
                    "Id": "invocations",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": namespace,
                            "MetricName": "InvocationCount",
                        },
                        "Period": 86400,        # daily
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                }],
                StartTime=datetime.combine(start, time.min),
                EndTime=datetime.combine(end, time.max),
            )

            # Q does not return per-user via CloudWatch. For per-user data
            # use AWS IAM Identity Center audit logs streamed to S3.
            records = []
            data = response["MetricDataResults"][0]
            for ts, val in zip(data["Timestamps"], data["Values"]):
                records.append(UsageRecord(
                    day=ts.date(),
                    tool_id=self.meta.id,
                    tool_name=self.meta.name,
                    user_email="aggregate@aws",
                    team="Engineering",
                    lob="Engineering",
                    tokens=int(val) * 80,    # ~80 tok per invocation
                    sessions=int(val),
                ))
            return records
        """
        if not os.getenv("AWS_REGION"):
            return []
        return []

    def healthcheck(self) -> tuple[bool, str]:
        if not os.getenv("AWS_REGION"):
            return False, "AWS_REGION not set"
        return True, "AWS region configured"
