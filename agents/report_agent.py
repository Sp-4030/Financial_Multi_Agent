"""Create source-grounded report sections from extracted document data."""

from typing import Any


class ReportAgent:
    METRIC_LABELS = {
        "revenue": "Revenue",
        "net_profit": "Net profit",
        "operating_profit": "Operating profit",
        "total_assets": "Total assets",
        "total_liabilities": "Total liabilities",
        "debt": "Long-term debt",
        "eps": "Earnings per share",
    }

    def generate(
        self,
        metrics: dict[str, Any],
        red_flags: dict[str, Any] | None = None,
        document_name: str = "Source document",
    ) -> dict[str, Any]:
        """Generate an executive summary and key financials without adding facts."""
        flags = (red_flags or {}).get("potential_red_flag_items", [])
        available_metrics = [
            (label, metrics.get(key))
            for key, label in self.METRIC_LABELS.items()
            if metrics.get(key) is not None
        ]

        if available_metrics:
            key_items = ", ".join(
                f"{label}: {value}" for label, value in available_metrics[:3]
            )
            summary = f"Reported financial figures include {key_items}."
        else:
            summary = "No key financial figures were extracted from the source document."

        if flags:
            issue_names = ", ".join(flag.get("type", "Financial concern") for flag in flags)
            summary += f" The automated review identified potential items for review: {issue_names}."
        elif red_flags is not None:
            summary += " The automated review did not identify a potential red flag."

        key_financials = [
            {
                "metric": label,
                "value": metrics[key],
                "source": document_name,
            }
            for key, label in self.METRIC_LABELS.items()
            if metrics.get(key) is not None
        ]
        ratios = metrics.get("financial_ratios", {})
        key_financials.extend(
            {
                "metric": label,
                "value": ratios.get(key),
                "source": document_name,
            }
            for key, label in (
                ("profit_margin", "Profit margin (%)"),
                ("roe", "Return on equity (%)"),
                ("roa", "Return on assets (%)"),
            )
            if ratios.get(key) is not None
        )

        return {
            "title": f"Financial Report — {document_name}",
            "source": document_name,
            "sections": [
                {"heading": "Executive Summary", "content": summary},
                {"heading": "Key Financials", "items": key_financials},
            ],
            "executive_summary": summary,
            "key_financials": key_financials,
        }