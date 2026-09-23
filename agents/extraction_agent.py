import re


class ExtractionAgent:

    def __init__(self):
        pass

    def extract_metrics(self, text):
        """
        Extract basic financial metrics from document text.
        """

        metrics = {
            "revenue": None,
            "profit": None,
            "expenses": None,
            "financial_ratios": {},
            "kpis": [],
            "revenue_trend": None,
        }

        # Revenue
        revenue_match = re.search(
            r"revenue\s*[:\-]?\s*([$₹€]?\s?[\d,]+(?:\.\d+)?)", text, re.IGNORECASE
        )

        if revenue_match:
            metrics["revenue"] = revenue_match.group(1)

        # Profit
        profit_match = re.search(
            r"(?:net profit|profit)\s*[:\-]?\s*([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if profit_match:
            metrics["profit"] = profit_match.group(1)

        # Expenses
        expense_match = re.search(
            r"(?:total expenses|expenses)\s*[:\-]?\s*([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if expense_match:
            metrics["expenses"] = expense_match.group(1)

        return metrics
