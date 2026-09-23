import re


class ExtractionAgent:

    def __init__(self):
        pass

    # Clean Financial Number
    def clean_number(self, value):

        if value is None:
            return None

        value = re.sub(r"[₹$€,]", "", value)
        value = value.strip()

        try:
            return float(value)
        except ValueError:
            return None

    # Extract Financial Metrics
    def extract_metrics(self, text):
        """
        Extract financial metrics from document text.
        """

        metrics = {
            "revenue": None,
            "net_profit": None,
            "operating_profit": None,
            "total_assets": None,
            "total_liabilities": None,
            "debt": None,
            "eps": None,
            "financial_ratios": {"profit_margin": None, "roe": None, "roa": None},
            "kpis": [],
            "revenue_trend": None,
        }

        # Revenue
        revenue_match = re.search(
            r"(?:revenue|total revenue)\s*[:\-]?\s*" r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if revenue_match:
            metrics["revenue"] = revenue_match.group(1)

        # Net Profit
        profit_match = re.search(
            r"(?:net profit|net income)\s*[:\-]?\s*" r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if profit_match:
            metrics["net_profit"] = profit_match.group(1)

        # Operating Profit
        operating_profit_match = re.search(
            r"(?:operating profit|operating income)\s*[:\-]?\s*"
            r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if operating_profit_match:
            metrics["operating_profit"] = operating_profit_match.group(1)

        # Total Assets
        assets_match = re.search(
            r"total assets\s*[:\-]?\s*" r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if assets_match:
            metrics["total_assets"] = assets_match.group(1)

        # Total Liabilities
        liabilities_match = re.search(
            r"total liabilities\s*[:\-]?\s*" r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if liabilities_match:
            metrics["total_liabilities"] = liabilities_match.group(1)

        # Debt
        debt_match = re.search(
            r"(?:total debt|debt)\s*[:\-]?\s*" r"([$₹€]?\s?[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if debt_match:
            metrics["debt"] = debt_match.group(1)

        # EPS
        eps_match = re.search(
            r"(?:EPS|earnings per share)\s*[:\-]?\s*" r"([$₹€]?\s?[\d,.]+)",
            text,
            re.IGNORECASE,
        )

        if eps_match:
            metrics["eps"] = eps_match.group(1)

        # Convert Values to Numbers
        revenue = self.clean_number(metrics["revenue"])

        net_profit = self.clean_number(metrics["net_profit"])

        total_assets = self.clean_number(metrics["total_assets"])

        # Profit Margin
        if revenue and net_profit is not None:

            metrics["financial_ratios"]["profit_margin"] = round(
                (net_profit / revenue) * 100, 2
            )

        # ROA
        if total_assets and net_profit is not None:

            metrics["financial_ratios"]["roa"] = round(
                (net_profit / total_assets) * 100, 2
            )

        # Return Result
        return metrics
