import re
from typing import Any, Optional


class ExtractionAgent:

    def __init__(self):
        pass

    # ==========================================
    # Clean Financial Number
    # ==========================================

    def clean_number(self, value):

        if value is None:
            return None

        value = re.sub(r"(?i)Rs\.?|INR|[₹$€£,]", "", str(value)).strip()
        is_parenthesized_negative = value.startswith("(") and value.endswith(")")
        if is_parenthesized_negative:
            value = value[1:-1].strip()

        try:
            number = float(value)
        except ValueError:
            return None
        return -abs(number) if is_parenthesized_negative else number

    # ==========================================
    # Extract First Number and Supporting Context
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

    def extract_number_with_evidence(self, pattern, text):
        """Extract matched value along with surrounding evidence text."""
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None, None
        val = match.group(1)
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        return val, snippet

    @staticmethod
    def detect_currency_and_scale(value_text: str, context_text: str = "") -> tuple[Optional[str], Optional[str]]:
        """Identify currency and scale/unit from value or context."""
        combined = f"{value_text} {context_text}".casefold()
        currency = next(
            (
                c for c, pat in (
                    ("INR", r"\binr\b|\brs\.?\b|₹"),
                    ("USD", r"\busd\b|\$"),
                    ("EUR", r"\beur\b|€"),
                    ("GBP", r"\bgbp\b|£"),
                )
                if re.search(pat, combined)
            ),
            None,
        )
        scale = next(
            (
                s for s, pat in (
                    ("Crore", r"\bcrores?\b|\bcr\b"),
                    ("Lakh", r"\blakhs?\b"),
                    ("Billion", r"\bbillions?\b|\bbn\b"),
                    ("Million", r"\bmillions?\b|\bmn\b"),
                    ("Thousand", r"\bthousands?\b|\bk\b"),
                )
                if re.search(pat, combined)
            ),
            None,
        )
        return currency, scale

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

    def extract_metrics(
        self,
        text: str,
        company: Optional[str] = None,
        document_name: Optional[str] = None,
        page_number: Optional[int] = None,
        prior_metrics: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:

        metrics = {
            "financial_year": None,
            "company": company,
            "document_name": document_name,
            "page_number": page_number,
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
                "operating_margin": None,
                "roe": None,
                "roa": None,
                "debt_to_assets": None,
                "liabilities_to_assets": None,
                "revenue_growth": None,
            },

            "metric_details": {},
            "calculated_metrics": [],
            "kpis": [],
            "revenue_trend": None
        }

        # ==========================================
        # Number Pattern
        # ==========================================

        number_pattern = (
            r"((?:(?:[$₹€£]|Rs\.?|INR)\s*)?\(?-?(?:(?:[$₹€£]|Rs\.?|INR)\s*)?\d[\d,]*(?:\.\d+)?\)?)"
        )

        income_labels = [
            r"\b(?:(?:total\s+)?revenues?|revenue\s+from\s+operations|turnover|net\s+sales)\b\s*:?\s*"
            + number_pattern,
            r"\b(?:net\s+income|net\s+profit|profit\s+after\s+tax(?:\s*\([^)]*\))?|profit\s+for\s+the\s+(?:year|period))\b\s*:?\s*"
            + number_pattern,
            r"\bnet\s+profit\s*\(after\s+non-controlling\s+interest\)\s*:?\s*"
            + number_pattern,
            r"\b(?:operating\s+income|operating\s+profit|income\s+from\s+operations|profit\s+before\s+interest\s+and\s+tax)\b\s*:?\s*" + number_pattern,
        ]
        income_text = self._section_with_best_match(
            text,
            r"\bconsolidated\s+(?:income\s+statements?|statements?\s+of\s+(?:income|operations|profit\s+and\s+loss)|statement\s+of\s+profit\s+and\s+loss|profit\s+and\s+loss\s+account)\b",
            income_labels,
        )
        balance_labels = [
            r"\btotal\s+assets\b\s*:?\s*" + number_pattern,
            r"\btotal\s+liabilit(?:ies|es)\b\s*:?\s*" + number_pattern,
            r"\b(?:(?:long[- ]term|short[- ]term|current)\s+)?(?:total\s+)?(?:debt|borrowings)\b\s*:?\s*"
            + number_pattern,
            r"\b(?:total\s+)?(?:shareholders'?|stockholders'?)\s+equity\b\s*:?\s*"
            + number_pattern,
        ]
        balance_text = self._section_with_best_match(
            text,
            r"\bconsolidated\s+balance\s+sheets?\b|\bstatement\s+of\s+financial\s+position\b",
            balance_labels,
        )

        # Global currency and scale hints from the top of the financial statements
        header_context = text[:3000]
        doc_currency, doc_scale = self.detect_currency_and_scale("", header_context)

        # Financial Year
        financial_year = re.search(
            r"\b(?:financial\s+year|fiscal\s+year|FY)\s*[:.]?\s*"
            r"(20\d{2})(?:\s*[-/]\s*(?:20)?\d{2})?\b",
            text,
            re.IGNORECASE,
        )
        if not financial_year:
            financial_year = re.search(
                r"\b(?:fiscal\s+year|financial\s+year|years?)\s+ended\s+[A-Za-z]+\s+\d{1,2},?\s*(20\d{2})\b",
                text,
                re.IGNORECASE,
            )
        if not financial_year:
            financial_year = re.search(
                r"\b(?:annual\s+report|10-k|form\s+10-k|integrated\s+report)[^\n\r]{0,80}?\b(20\d{2})\b",
                text,
                re.IGNORECASE,
            )
        if financial_year:
            metrics["financial_year"] = financial_year.group(1)

        # Helper to register detailed metric
        def register_metric(name: str, label: str, val_str: Optional[str], evidence_str: Optional[str], default_section: str = ""):
            if not val_str:
                return
            metrics[name] = val_str
            curr, sc = self.detect_currency_and_scale(val_str, evidence_str or default_section[:300])
            curr = curr or doc_currency
            sc = sc or doc_scale
            unit_str = f"{curr} {sc}".strip() if (curr or sc) else "As reported"
            metrics["metric_details"][name] = {
                "name": label,
                "raw_value": val_str,
                "numeric_value": self.clean_number(val_str),
                "currency": curr,
                "scale": sc,
                "unit": unit_str,
                "evidence": evidence_str or "Extracted from financial statements.",
                "financial_year": metrics["financial_year"],
                "company": company,
                "document": document_name,
                "page_number": page_number,
                "is_calculated": False,
            }

        # ==========================================
        # Revenue
        # ==========================================
        rev_val, rev_ev = self.extract_number_with_evidence(
            r"\b(?:(?:total\s+)?revenues?|revenue\s+from\s+operations|turnover|net\s+sales)\b\s*:?\s*"
            + number_pattern,
            income_text,
        )
        register_metric("revenue", "Revenue", rev_val, rev_ev, income_text)

        # ==========================================
        # Net Profit / Net Income
        # ==========================================
        net_val, net_ev = self.extract_number_with_evidence(
            r"\bnet\s+profit\s*\(after\s+non-controlling\s+interest\)\s*:?\s*"
            + number_pattern,
            income_text,
        )
        if not net_val:
            net_val, net_ev = self.extract_number_with_evidence(
                r"\b(?:net\s+income|net\s+profit|profit\s+after\s+tax(?:\s*\([^)]*\))?|profit\s+for\s+the\s+(?:year|period))\s*:?\s*"
                + number_pattern,
                income_text,
            )
        register_metric("net_profit", "Net profit", net_val, net_ev, income_text)

        # ==========================================
        # Operating Profit
        # ==========================================
        op_val, op_ev = self.extract_number_with_evidence(
            r"\b(?:income\s+from\s+operations|operating\s+income|operating\s+profit|profit\s+before\s+interest\s+and\s+tax)\b\s*:?\s*"
            + number_pattern,
            income_text,
        )
        register_metric("operating_profit", "Operating profit", op_val, op_ev, income_text)

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
            eps_val = eps_match.group(1)
            start = max(0, eps_match.start() - 60)
            end = min(len(income_text), eps_match.end() + 60)
            eps_ev = re.sub(r"\s+", " ", income_text[start:end]).strip()
            register_metric("eps", "Earnings per share", eps_val, eps_ev, income_text)

        # ==========================================
        # Total Assets
        # ==========================================
        assets_val, assets_ev = self.extract_number_with_evidence(
            r"\btotal\s+assets\b\s*:?\s*" + number_pattern,
            balance_text,
        )
        register_metric("total_assets", "Total assets", assets_val, assets_ev, balance_text)

        # ==========================================
        # Total Liabilities
        # ==========================================
        liab_val, liab_ev = self.extract_number_with_evidence(
            r"\btotal\s+liabilit(?:ies|es)\b\s*:?\s*" + number_pattern,
            balance_text,
        )
        register_metric("total_liabilities", "Total liabilities", liab_val, liab_ev, balance_text)

        # ==========================================
        # Shareholders' Equity
        # ==========================================
        eq_val, eq_ev = self.extract_number_with_evidence(
            r"\b(?:total\s+)?(?:shareholders'?|stockholders'?)\s+equity\b\s*:?\s*"
            + number_pattern,
            balance_text,
        )
        register_metric("shareholders_equity", "Shareholders' equity", eq_val, eq_ev, balance_text)

        # ==========================================
        # Debt / Borrowings
        # ==========================================
        debt_val, debt_ev = self.extract_number_with_evidence(
            r"\b(?:(?:long[- ]term|short[- ]term|current)\s+)?(?:total\s+)?(?:debt|borrowings)\b\s*:?\s*"
            + number_pattern,
            balance_text,
        )
        register_metric("debt", "Debt", debt_val, debt_ev, balance_text)

        # ==========================================
        # Numeric Cleaned Values for Derived Calculations
        # ==========================================
        revenue_value = self.clean_number(metrics["revenue"])
        net_profit_value = self.clean_number(metrics["net_profit"])
        operating_profit_value = self.clean_number(metrics["operating_profit"])
        total_assets_value = self.clean_number(metrics["total_assets"])
        total_liabilities_value = self.clean_number(metrics["total_liabilities"])
        equity_value = self.clean_number(metrics["shareholders_equity"])
        debt_value = self.clean_number(metrics["debt"])

        # ==========================================
        # Net Profit Margin (Calculated)
        # ==========================================
        if revenue_value is not None and net_profit_value is not None and revenue_value != 0:
            pm = round((net_profit_value / revenue_value) * 100, 2)
            metrics["financial_ratios"]["profit_margin"] = pm
            metrics["calculated_metrics"].append({
                "metric": "Net profit margin",
                "formula": "net profit / revenue x 100",
                "result_percent": pm,
                "inputs": {
                    "net_profit": metrics["net_profit"],
                    "revenue": metrics["revenue"],
                },
                "period": metrics["financial_year"],
                "source": document_name or "Financial statements",
                "is_calculated": True,
            })

        # ==========================================
        # Operating Margin (Calculated)
        # ==========================================
        if revenue_value is not None and operating_profit_value is not None and revenue_value != 0:
            om = round((operating_profit_value / revenue_value) * 100, 2)
            metrics["financial_ratios"]["operating_margin"] = om
            metrics["calculated_metrics"].append({
                "metric": "Operating margin",
                "formula": "operating profit / revenue x 100",
                "result_percent": om,
                "inputs": {
                    "operating_profit": metrics["operating_profit"],
                    "revenue": metrics["revenue"],
                },
                "period": metrics["financial_year"],
                "source": document_name or "Financial statements",
                "is_calculated": True,
            })

        # ==========================================
        # Return on Assets (ROA) (Calculated)
        # ==========================================
        if total_assets_value is not None and net_profit_value is not None and total_assets_value != 0:
            roa = round((net_profit_value / total_assets_value) * 100, 2)
            metrics["financial_ratios"]["roa"] = roa
            metrics["calculated_metrics"].append({
                "metric": "Return on Assets (ROA)",
                "formula": "net profit / total assets x 100",
                "result_percent": roa,
                "inputs": {
                    "net_profit": metrics["net_profit"],
                    "total_assets": metrics["total_assets"],
                },
                "period": metrics["financial_year"],
                "source": document_name or "Financial statements",
                "is_calculated": True,
            })

        # ==========================================
        # Return on Equity (ROE) (Calculated)
        # ==========================================
        if equity_value is not None and net_profit_value is not None and equity_value != 0:
            roe = round((net_profit_value / equity_value) * 100, 2)
            metrics["financial_ratios"]["roe"] = roe
            metrics["calculated_metrics"].append({
                "metric": "Return on Equity (ROE)",
                "formula": "net profit / shareholders' equity x 100",
                "result_percent": roe,
                "inputs": {
                    "net_profit": metrics["net_profit"],
                    "shareholders_equity": metrics["shareholders_equity"],
                },
                "period": metrics["financial_year"],
                "source": document_name or "Financial statements",
                "is_calculated": True,
            })

        # ==========================================
        # Debt to Assets & Liabilities to Assets (Calculated)
        # ==========================================
        if total_assets_value is not None and total_assets_value != 0:
            if debt_value is not None:
                d2a = round((debt_value / total_assets_value) * 100, 2)
                metrics["financial_ratios"]["debt_to_assets"] = d2a
                metrics["calculated_metrics"].append({
                    "metric": "Debt to assets",
                    "formula": "debt / total assets x 100",
                    "result_percent": d2a,
                    "inputs": {
                        "debt": metrics["debt"],
                        "total_assets": metrics["total_assets"],
                    },
                    "period": metrics["financial_year"],
                    "source": document_name or "Financial statements",
                    "is_calculated": True,
                })
            if total_liabilities_value is not None:
                l2a = round((total_liabilities_value / total_assets_value) * 100, 2)
                metrics["financial_ratios"]["liabilities_to_assets"] = l2a
                metrics["calculated_metrics"].append({
                    "metric": "Liabilities to assets",
                    "formula": "total liabilities / total assets x 100",
                    "result_percent": l2a,
                    "inputs": {
                        "total_liabilities": metrics["total_liabilities"],
                        "total_assets": metrics["total_assets"],
                    },
                    "period": metrics["financial_year"],
                    "source": document_name or "Financial statements",
                    "is_calculated": True,
                })

        # ==========================================
        # Revenue Growth (if prior metrics supplied with comparable unit)
        # ==========================================
        if prior_metrics and revenue_value is not None:
            prior_rev = self.clean_number(prior_metrics.get("revenue"))
            if prior_rev and prior_rev > 0:
                rev_growth = round(((revenue_value - prior_rev) / prior_rev) * 100, 2)
                metrics["financial_ratios"]["revenue_growth"] = rev_growth
                metrics["calculated_metrics"].append({
                    "metric": "Revenue growth",
                    "formula": "(current revenue - prior revenue) / prior revenue x 100",
                    "result_percent": rev_growth,
                    "inputs": {
                        "current_revenue": metrics["revenue"],
                        "prior_revenue": prior_metrics.get("revenue"),
                    },
                    "period": f"{prior_metrics.get('financial_year', 'Prior')} -> {metrics['financial_year']}",
                    "source": document_name or "Financial statements",
                    "is_calculated": True,
                })

        return metrics