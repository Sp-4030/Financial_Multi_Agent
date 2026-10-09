"""Create source-grounded report sections from extracted document data."""

import re
from typing import Any

from agents.extraction_agent import ExtractionAgent


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
    TREND_METRICS = {
        "revenue": "Revenue",
        "net_profit": "Net profit",
        "operating_profit": "Operating profit",
    }

    @staticmethod
    def _trend_unit(value: Any) -> tuple[str, str] | None:
        text = str(value or "").casefold()
        currency = next(
            (
                unit
                for unit, pattern in (
                    ("INR", r"\binr\b|\brs\.?\b|₹"),
                    ("USD", r"\busd\b|\$"),
                    ("EUR", r"\beur\b|€"),
                    ("GBP", r"\bgbp\b|£"),
                )
                if re.search(pattern, text)
            ),
            None,
        )
        scale = next(
            (
                unit
                for unit, pattern in (
                    ("crore", r"\bcrores?\b"),
                    ("lakh", r"\blakhs?\b"),
                    ("billion", r"\bbillions?\b|\bbn\b"),
                    ("million", r"\bmillions?\b|\bmn\b"),
                    ("thousand", r"\bthousands?\b"),
                )
                if re.search(pattern, text)
            ),
            None,
        )
        return (currency, scale) if currency and scale else None

    def _build_trends(self, comparison_documents):
        extractor = ExtractionAgent()
        trends = []
        for metric, label in self.TREND_METRICS.items():
            grouped: dict[str, list[dict[str, Any]]] = {}
            for document in comparison_documents:
                year = str(document.get("financial_year") or "")
                if not year.isdigit():
                    continue
                value = (document.get("metrics") or {}).get(metric)
                numeric_text = re.sub(
                    r"\b(?:USD|EUR|GBP|INR|crores?|lakhs?|millions?|billions?|"
                    r"thousands?|mn|bn)\b",
                    "",
                    str(value or ""),
                    flags=re.IGNORECASE,
                )
                numeric = (
                    extractor.clean_number(numeric_text) if value is not None else None
                )
                if numeric is None:
                    continue
                grouped.setdefault(
                    str(document.get("company") or "Unknown"), []
                ).append(
                    {
                        "financial_year": year,
                        "value": value,
                        "numeric_value": numeric,
                        "source": document.get("document", "Unknown"),
                        "unit": self._trend_unit(value),
                    }
                )

            for company, observations in grouped.items():
                observations.sort(key=lambda item: int(item["financial_year"]))
                direction = "Not inferred: two comparable periods are unavailable."
                financial_years = {
                    item["financial_year"] for item in observations
                }
                if len(observations) >= 2 and len(financial_years) < len(observations):
                    direction = (
                        "Not inferred: multiple source documents report the same "
                        "financial year."
                    )
                elif len(observations) >= 2:
                    units = {item["unit"] for item in observations}
                    if len(units) == 1 and None not in units:
                        first = observations[0]["numeric_value"]
                        latest = observations[-1]["numeric_value"]
                        direction = (
                            "increased" if latest > first
                            else "decreased" if latest < first
                            else "was unchanged"
                        )
                    else:
                        direction = (
                            "Not inferred: currency or scale is missing or differs "
                            "between reported values."
                        )
                trends.append(
                    {
                        "company": company,
                        "metric": label,
                        "observations": [
                            {
                                "financial_year": item["financial_year"],
                                "value": item["value"],
                                "source": item["source"],
                            }
                            for item in observations
                        ],
                        "direction": direction,
                    }
                )
        return trends

    def generate(
        self,
        metrics: dict[str, Any],
        red_flags: dict[str, Any] | None = None,
        document_name: str = "Source document",
        comparison: dict[str, Any] | None = None,
        findings: list[dict[str, Any]] | None = None,
        research_findings: list[dict[str, Any]] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Assemble report sections only from extracted or supplied source data."""
        has_red_flag_analysis = red_flags is not None
        red_flags = red_flags or {}
        flags = red_flags.get("potential_red_flag_items", [])
        all_findings = findings if findings is not None else red_flags.get("red_flags", [])
        available_metrics = [
            (label, metrics.get(key))
            for key, label in self.METRIC_LABELS.items()
            if metrics.get(key) is not None
        ]
        missing_metrics = [
            label
            for key, label in self.METRIC_LABELS.items()
            if metrics.get(key) is None
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
        elif has_red_flag_analysis:
            summary += " The automated review did not identify a potential red flag."

        source_label = (
            document_name if sources else "Source reference unavailable"
        )
        key_financials = [
            {
                "metric": label,
                "value": metrics[key],
                "source": source_label,
            }
            for key, label in self.METRIC_LABELS.items()
            if metrics.get(key) is not None
        ]
        ratios = metrics.get("financial_ratios", {})
        key_financials.extend(
            {
                "metric": label,
                "value": ratios.get(key),
                "source": source_label,
            }
            for key, label in (
                ("profit_margin", "Profit margin (%)"),
                ("roe", "Return on equity (%)"),
                ("roa", "Return on assets (%)"),
            )
            if ratios.get(key) is not None
        )

        risk_findings = [
            {
                "type": flag.get("type", "Financial concern"),
                "severity": flag.get("severity", "Unspecified"),
                "message": flag.get("message", "No description supplied."),
                "evidence": flag.get("evidence") or "Supporting evidence unavailable.",
            }
            for flag in all_findings
        ]
        comparisons = (comparison or {}).get("documents", [])
        trends = self._build_trends(comparisons)
        trend_summary = (
            trends
            if trends
            else [
                "Trend analysis was not possible because multiple years of "
                "comparable extracted metrics were unavailable."
            ]
        )
        source_documents = sources or []
        comparison_rows = [
            {
                "company": document.get("company"),
                "financial_year": document.get("financial_year"),
                "document": document.get("document"),
                "metrics": document.get("metrics", {}),
            }
            for document in comparisons
        ]
        sourced_research = [
            {
                "question": item.get("question", "Research question"),
                "answer": item.get("answer", "No answer supplied."),
                "sources": item.get("sources", []),
            }
            for item in (research_findings or [])
        ]
        limitations = []
        if missing_metrics:
            limitations.append(
                "Not extracted from the selected source: "
                + ", ".join(missing_metrics)
                + "."
            )
        if not sources:
            limitations.append("Source document references were not supplied.")
        if metrics.get("financial_year") is None:
            limitations.append("The reporting period was not identified.")
        limitations.append(
            "Extracted values retain their source representation; units and scales "
            "are not normalized."
        )
        if not trends:
            limitations.append(
                "Year-over-year trends were not assessed because comparable "
                "multi-year metrics were unavailable."
            )

        return {
            "title": f"Financial Report — {document_name}",
            "source": document_name,
            "company": metrics.get("company"),
            "financial_year": metrics.get("financial_year"),
            "financial_metrics": metrics,
            "sections": [
                {"heading": "Executive Summary", "content": summary},
                {"heading": "Key Financials", "items": key_financials},
                {"heading": "Risks and Findings", "items": risk_findings},
                {"heading": "Research Findings", "items": sourced_research},
                {"heading": "Company Comparison", "items": comparison_rows},
                {"heading": "Ratios and Trends", "items": trend_summary},
                {"heading": "Source Documents", "items": source_documents},
                {"heading": "Missing Information and Limitations", "items": limitations},
            ],
            "executive_summary": summary,
            "key_financials": key_financials,
            "red_flags": risk_findings,
            "comparison": comparison_rows,
            "trends": trends,
            "findings": risk_findings,
            "research_findings": sourced_research,
            "sources": source_documents,
            "missing_information": missing_metrics,
            "limitations": limitations,
        }