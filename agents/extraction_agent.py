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

        value = re.sub(r"(?i)Rs\.?|INR|[₹$€,]", "", value).strip()
        is_parenthesized_negative = value.startswith("(") and value.endswith(")")
        if is_parenthesized_negative:
            value = value[1:-1].strip()

        try:
            number = float(value)
        except ValueError:
            return None
        return -abs(number) if is_parenthesized_negative else number

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

    @staticmethod
    def _section_with_best_match(text, heading_pattern, label_patterns):
        headings = list(re.finditer(heading_pattern, text, re.IGNORECASE))
        if not headings:
            return text

        best_section = text
        best_score = -1
        best_label_matches = 0
        for heading in headings:
            section = text[heading.start() : heading.start() + 5000]
            label_matches = sum(
                bool(re.search(pattern, section, re.IGNORECASE | re.DOTALL))
                for pattern in label_patterns
            )
            score = label_matches
            if re.search(
                r"\b(?:for the years ended|as of)\b",
                section[:300],
                re.IGNORECASE,
            ):
                score += 2
            if score > best_score:
                best_score = score
                best_label_matches = label_matches
                best_section = section
        return best_section if best_label_matches else text

    # ==========================================
    # Extract Financial Metrics
    # ==========================================

    def extract_metrics(self, text):

        metrics = {
            "financial_year": None,
            "revenue": None,
            "net_profit": None,
            "operating_profit": None,
            "total_assets": None,
            "total_liabilities": None,
            "shareholders_equity": None,
            "debt": None,
            "eps": None,

            "financial_ratios": {
                "profit_margin": None,
                "roe": None,
                "roa": None,
                "debt_to_assets": None,
                "liabilities_to_assets": None,
            },

            "kpis": [],
            "revenue_trend": None
        }

        # ==========================================
        # Number Pattern
        # ==========================================

        number_pattern = (
            r"((?:(?:[$₹€]|Rs\.?|INR)\s*)?\(?-?(?:(?:[$₹€]|Rs\.?|INR)\s*)?\d[\d,]*(?:\.\d+)?\)?)"
        )

        income_labels = [
            r"\b(?:(?:total\s+)?revenues?|revenue\s+from\s+operations)\b\s*:?\s*"
            + number_pattern,
            r"\bnet\s+income\b\s*:?\s*" + number_pattern,
            r"\bnet\s+profit\s*\(after\s+non-controlling\s+interest\)\s*:?\s*"
            + number_pattern,
            r"\b(?:operating\s+income|income\s+from\s+operations)\b\s*:?\s*" + number_pattern,
            r"\bprofit\s+(?:after\s+tax(?:\s*\([^)]*\))?|for\s+the\s+(?:year|period))\s*:?\s*"
            + number_pattern,
        ]
        income_text = self._section_with_best_match(
            text,
            r"\bconsolidated\s+(?:income\s+statements?|statements?\s+of\s+(?:income|operations|profit\s+and\s+loss)|statement\s+of\s+profit\s+and\s+loss)\b",
            income_labels,
        )
        balance_labels = [
            r"\btotal\s+assets\b\s*:?\s*" + number_pattern,
            r"\btotal\s+liabilit(?:ies|es)\b\s*:?\s*" + number_pattern,
            r"\b(?:long[- ]term|short[- ]term|current)?\s*(?:debt|borrowings)\b\s*:?\s*"
            + number_pattern,
            r"\b(?:total\s+)?(?:shareholders'?|stockholders'?)\s+equity\b\s*:?\s*"
            + number_pattern,
        ]
        balance_text = self._section_with_best_match(
            text,
            r"\bconsolidated\s+balance\s+sheets?\b",
            balance_labels,
        )

        financial_year = re.search(
            r"\b(?:financial\s+year|fiscal\s+year|FY)\s*[:.]?\s*"
            r"(20\d{2})(?:\s*[-/]\s*(?:20)?\d{2})?\b",
            text,
            re.IGNORECASE,
        )
        if financial_year:
            metrics["financial_year"] = financial_year.group(1)

        # ==========================================
        # Revenue
        # ==========================================

        revenue = self.extract_number(
            r"\b(?:(?:total\s+)?revenues?|revenue\s+from\s+operations)\b\s*:?\s*"
            + number_pattern,
            income_text,
        )

        if revenue:
            metrics["revenue"] = revenue

        # ==========================================
        # Net Income
        # ==========================================

        net_profit = self.extract_number(
            r"\bnet\s+profit\s*\(after\s+non-controlling\s+interest\)\s*:?\s*"
            + number_pattern,
            income_text,
        ) or self.extract_number(
            r"\b(?:net\s+income|net\s+profit|profit\s+after\s+tax(?:\s*\([^)]*\))?|profit\s+for\s+the\s+(?:year|period))\s*:?\s*"
            + number_pattern,
            income_text,
        )

        if net_profit:
            metrics["net_profit"] = net_profit

        # ==========================================
        # Operating Profit
        # ==========================================

        operating_profit = self.extract_number(
            r"\b(?:income\s+from\s+operations|operating\s+income|operating\s+profit)\b\s*:?\s*"
            + number_pattern,
            income_text,
        )

        if operating_profit:
            metrics["operating_profit"] = operating_profit

        # ==========================================
        # EPS
        # ==========================================

        eps_match = re.search(
            r"\b(?:(?:basic|diluted)\s+)?earnings\s+per\s+share\b"
            r"(?:\s*\([^)]*\))?\s*:?\s*" + number_pattern,
            income_text,
            re.IGNORECASE,
        )

        if not eps_match:
            eps_match = re.search(
                r"\b(?:basic|diluted)\s+EPS\b\s*:?\s*" + number_pattern,
                income_text,
                re.IGNORECASE,
            )
        if eps_match:
            metrics["eps"] = eps_match.group(1)

        # ==========================================
        # Total Assets
        # ==========================================

        total_assets = self.extract_number(
            r"\btotal\s+assets\b\s*:?\s*" + number_pattern,
            balance_text,
        )

        if total_assets:
            metrics["total_assets"] = total_assets

        # ==========================================
        # Total Liabilities
        # ==========================================

        total_liabilities = self.extract_number(
            r"\btotal\s+liabilit(?:ies|es)\b\s*:?\s*" + number_pattern,
            balance_text,
        )

        if total_liabilities:
            metrics["total_liabilities"] = total_liabilities

        shareholders_equity = self.extract_number(
            r"\b(?:total\s+)?(?:shareholders'?|stockholders'?)\s+equity\b"
            r"\s*:?\s*" + number_pattern,
            balance_text,
        )
        if shareholders_equity:
            metrics["shareholders_equity"] = shareholders_equity

        # ==========================================
        # Long-Term Debt
        # ==========================================

        debt = self.extract_number(
            r"\b(?:(?:long[- ]term|short[- ]term|current)\s+)?"
            r"(?:total\s+)?(?:debt|borrowings)\b\s*:?\s*" + number_pattern,
            balance_text,
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
        total_liabilities_value = self.clean_number(
            metrics["total_liabilities"]
        )
        equity_value = self.clean_number(metrics["shareholders_equity"])
        debt_value = self.clean_number(metrics["debt"])

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

        if (
            equity_value is not None
            and net_profit_value is not None
            and equity_value != 0
        ):
            metrics["financial_ratios"]["roe"] = round(
                (net_profit_value / equity_value) * 100,
                2,
            )

        if total_assets_value is not None and total_assets_value != 0:
            if debt_value is not None:
                metrics["financial_ratios"]["debt_to_assets"] = round(
                    debt_value / total_assets_value * 100, 2
                )
            if total_liabilities_value is not None:
                metrics["financial_ratios"]["liabilities_to_assets"] = round(
                    total_liabilities_value / total_assets_value * 100, 2
                )

        # ==========================================
        # Return Result
        # ==========================================

        return metrics