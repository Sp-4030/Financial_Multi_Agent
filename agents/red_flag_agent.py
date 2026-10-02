import re


class RedFlagAgent:

    def __init__(self):
        pass

    def analyze(self, text, extracted_metrics=None):
        """
        Analyze financial document text and extracted metrics
        to identify potential financial red flags.
        """

        red_flags = []

        # 1. Rising Debt
        debt_pattern = re.search(
            r"(?:debt|total debt)"
            r".{0,100}"
            r"(\d[\d,]*(?:\.\d+)?)"
            r".{0,100}"
            r"(\d[\d,]*(?:\.\d+)?)",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if debt_pattern:

            try:
                old_debt = float(debt_pattern.group(1).replace(",", ""))

                new_debt = float(debt_pattern.group(2).replace(",", ""))

                if new_debt > old_debt:

                    red_flags.append(
                        {
                            "type": "Rising Debt",
                            "severity": "Medium",
                            "message": (
                                "Debt appears to be increasing "
                                "in the financial document."
                            ),
                        }
                    )

            except ValueError:
                pass

        # 2. Falling Profit Margin
        margin_pattern = re.search(
            r"(?:profit margin|net margin)"
            r".{0,100}"
            r"(\d+(?:\.\d+)?)\s*%"
            r".{0,100}"
            r"(\d+(?:\.\d+)?)\s*%",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if margin_pattern:

            try:
                old_margin = float(margin_pattern.group(1))

                new_margin = float(margin_pattern.group(2))

                if new_margin < old_margin:

                    red_flags.append(
                        {
                            "type": "Falling Profit Margin",
                            "severity": "Medium",
                            "message": ("Profit margin appears to be " "declining."),
                        }
                    )

            except ValueError:
                pass

        # 3. Auditor Qualification
        auditor_keywords = [
            "qualified opinion",
            "qualification in audit",
            "qualified audit opinion",
            "material misstatement",
            "material uncertainty",
            "going concern",
            "adverse opinion",
            "disclaimer of opinion",
        ]

        text_lower = text.lower()

        for keyword in auditor_keywords:

            if keyword in text_lower:

                red_flags.append(
                    {
                        "type": "Auditor Qualification",
                        "severity": "High",
                        "message": (
                            f"Potential auditor-related issue detected: " f"{keyword}."
                        ),
                    }
                )

                break

        # 4. Unusual Financial Patterns
        unusual_keywords = [
            "significant decline",
            "substantial decline",
            "unusual transaction",
            "impairment loss",
            "restructuring charge",
            "exceptional loss",
            "fraud",
            "investigation",
        ]

        for keyword in unusual_keywords:

            if keyword in text_lower:

                red_flags.append(
                    {
                        "type": "Unusual Financial Pattern",
                        "severity": "High",
                        "message": (
                            f"Potential unusual financial pattern "
                            f"detected: {keyword}."
                        ),
                    }
                )

        # 5. Low Profit Margin
        if extracted_metrics:

            ratios = extracted_metrics.get("financial_ratios", {})

            profit_margin = ratios.get("profit_margin")

            if profit_margin is not None and profit_margin < 5:

                red_flags.append(
                    {
                        "type": "Low Profit Margin",
                        "severity": "Medium",
                        "message": (
                            f"Profit margin is relatively low " f"at {profit_margin}%."
                        ),
                    }
                )

        # Final Result
        return {"total_flags": len(red_flags), "red_flags": red_flags}
