import re


class ExtractionAgent:

    def __init__(self):
        pass

    # ==========================================
    # Clean Financial Number
    # ==========================================

    def clean_number(self, value):

        if value is None:
            return None

        value = re.sub(r"[₹$€,]", "", value)
        value = value.strip()

        try:
            return float(value)
        except ValueError:
            return None

    # ==========================================
    # Extract First Number
    # ==========================================

    def extract_number(self, pattern, text):

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        return None

    # ==========================================
    # Extract Financial Metrics
    # ==========================================

    def extract_metrics(self, text):

        metrics = {
            "revenue": None,
            "net_profit": None,
            "operating_profit": None,
            "total_assets": None,
            "total_liabilities": None,
            "debt": None,
            "eps": None,

            "financial_ratios": {
                "profit_margin": None,
                "roe": None,
                "roa": None
            },

            "kpis": [],
            "revenue_trend": None
        }

        # ==========================================
        # Number Pattern
        # ==========================================

        number_pattern = (
            r"([$₹€]?\s?\d[\d,]*(?:\.\d+)?)"
        )

        # ==========================================
        # Find Income Statement
        # ==========================================

        income_start = re.search(
            r"CONSOLIDATED STATEMENTS OF INCOME",
            text,
            re.IGNORECASE
        )

        income_end = re.search(
            r"CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
            text,
            re.IGNORECASE
        )

        # ==========================================
        # Income Statement Section
        # ==========================================

        if income_start:

            start = income_start.start()

            if income_end:
                end = income_end.start()
                income_text = text[start:end]

            else:
                income_text = text[start:start + 15000]

        else:

            # Fallback
            income_text = text

        # ==========================================
        # Find Balance Sheet
        # ==========================================

        balance_start = re.search(
            r"CONSOLIDATED BALANCE SHEETS",
            text,
            re.IGNORECASE
        )

        # ==========================================
        # Balance Sheet Section
        # ==========================================

        if balance_start:

            balance_text = text[
                balance_start.start():
                balance_start.start() + 15000
            ]

        else:

            # Fallback
            balance_text = text

        # ==========================================
        # Revenue
        # ==========================================

        revenue = self.extract_number(
            r"\bRevenues?\b"
            r"\s+"
            + number_pattern,
            income_text
        )

        if revenue:
            metrics["revenue"] = revenue

        # ==========================================
        # Net Income
        # ==========================================

        net_profit = self.extract_number(
            r"\bNet income\b"
            r"\s+"
            + number_pattern,
            income_text
        )

        if net_profit:
            metrics["net_profit"] = net_profit

        # ==========================================
        # Operating Profit
        # ==========================================

        operating_profit = self.extract_number(
            r"(?:Income from operations|Operating income|Operating profit)"
            r"\s+"
            + number_pattern,
            income_text
        )

        if operating_profit:
            metrics["operating_profit"] = operating_profit

        # ==========================================
        # EPS
        # ==========================================

        eps_match = re.search(
            r"earnings\s+per\s+share"
            r"\s*"
            + number_pattern,
            income_text,
            re.IGNORECASE
        )

        if eps_match:
            metrics["eps"] = eps_match.group(1)

        # ==========================================
        # Total Assets
        # ==========================================

        total_assets = self.extract_number(
            r"\bTotal assets\b"
            r"\s+"
            + number_pattern,
            balance_text
        )

        if total_assets:
            metrics["total_assets"] = total_assets

        # ==========================================
        # Total Liabilities
        # ==========================================

        total_liabilities = self.extract_number(
            r"\bTotal liabilities\b"
            r"\s+"
            + number_pattern,
            balance_text
        )

        if total_liabilities:
            metrics["total_liabilities"] = total_liabilities

        # ==========================================
        # Long-Term Debt
        # ==========================================

        debt = self.extract_number(
            r"\bLong-term debt\b"
            r"\s+"
            + number_pattern,
            balance_text
        )

        if debt:
            metrics["debt"] = debt

        # ==========================================
        # Convert Values
        # ==========================================

        revenue_value = self.clean_number(
            metrics["revenue"]
        )

        net_profit_value = self.clean_number(
            metrics["net_profit"]
        )

        total_assets_value = self.clean_number(
            metrics["total_assets"]
        )

        # ==========================================
        # Profit Margin
        # ==========================================

        if (
            revenue_value is not None
            and net_profit_value is not None
            and revenue_value != 0
        ):

            metrics["financial_ratios"]["profit_margin"] = round(
                (net_profit_value / revenue_value) * 100,
                2
            )

        # ==========================================
        # ROA
        # ==========================================

        if (
            total_assets_value is not None
            and net_profit_value is not None
            and total_assets_value != 0
        ):

            metrics["financial_ratios"]["roa"] = round(
                (net_profit_value / total_assets_value) * 100,
                2
            )

        # ==========================================
        # Return Result
        # ==========================================

        return metrics