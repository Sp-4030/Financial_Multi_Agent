import re
import ollama


class RedFlagAgent:

    def __init__(self):

        # Local Ollama Model

        self.model = "llama3.2:latest"

    # Get Context Around Keyword

    def get_context(self, text, keyword, window=300):

        match = re.search(re.escape(keyword), text, re.IGNORECASE)

        if not match:
            return None

        start = max(0, match.start() - window)

        end = min(len(text), match.end() + window)

        context = text[start:end]

        context = re.sub(r"\s+", " ", context).strip()

        return context

    # Ollama AI Analysis

    def ai_analysis(self, context):

        if not context:
            return "No context available."

        prompt = f"""
You are a financial annual-report analysis assistant.

Analyze ONLY the provided document context.

Important rules:

1. A keyword alone is NOT a red flag.
2. Normal accounting policies are NOT automatically red flags.
3. Standard audit procedures are NOT red flags.
4. Generic risk disclosures are NOT confirmed red flags.
5. Generic statements about fraud are NOT evidence of fraud.
6. Generic statements about investigations are NOT evidence
   that the company is currently under investigation.
7. Do not assume fraud or wrongdoing.
8. Do not invent information.
9. Use only evidence present in the provided context.
10. Distinguish between:
    - normal accounting/disclosure language
    - potential financial concern
    - actual evidence of a significant issue
11. A potential red flag should be company-specific and supported
    by concrete evidence in the supplied context.
12. Risk-factor language describing what COULD or MAY happen
    in the future should normally be classified as No.
13. Internal-control statements saying controls cannot prevent
    all fraud or errors are normal disclosures and should
    normally be classified as No.
14. General regulatory compliance disclosures should normally
    be classified as No.
15. Audit procedures and PCAOB/SEC standard language should
    normally be classified as No.

Return EXACTLY this format:

Finding: <short description>

Potential Red Flag: <Yes or No>

Confidence: <High, Medium, or Low>

Reason: <short explanation>

Evidence: <important evidence from the context>

Document context:
{context}
"""

        try:

            response = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": prompt}]
            )

            return response["message"]["content"]

        except Exception as e:

            return f"Ollama analysis failed: {str(e)}"

    # Extract AI Decision

    def get_ai_decision(self, ai_result):

        if not ai_result:
            return "Unknown"

        match = re.search(r"Potential Red Flag:\s*(Yes|No)", ai_result, re.IGNORECASE)

        if match:

            return match.group(1).capitalize()

        return "Unknown"

    # Extract AI Confidence

    def get_ai_confidence(self, ai_result):

        if not ai_result:
            return "Unknown"

        match = re.search(r"Confidence:\s*(High|Medium|Low)", ai_result, re.IGNORECASE)

        if match:

            return match.group(1).capitalize()

        return "Unknown"

    # Check Generic Disclosure

    def is_generic_disclosure(self, context):

        if not context:
            return False

        context_lower = context.lower()

        generic_phrases = [
            "will not prevent or detect all errors and all fraud",
            "reasonable, not absolute, assurance",
            "reasonable assurance",
            "internal control over financial reporting",
            "disclosure controls",
            "risk of regulatory enforcement actions",
            "audits, investigations, or lawsuits",
            "enforcement actions taken by data protection authorities",
            "may result in significant financial penalties",
            "could result in significant financial penalties",
            "may result in penalties",
            "could result in penalties",
            "potential penalties",
            "risks associated with compliance",
            "compliance with additional data protection requirements",
            "applicable laws and regulations",
            "applicable rules and regulations",
            "risk factors",
            "regulatory requirements",
            "regulatory compliance",
            "standard audit procedures",
            "audit procedures",
            "control environment",
            "internal controls",
            "we cannot provide assurance",
            "not designed to detect all fraud",
            "subject to the inherent limitations of internal control",
        ]

        for phrase in generic_phrases:
            if phrase in context_lower:
                return True

        generic_patterns = [
            r"\b(?:we|the company)\s+(?:cannot|can not|do not)\s+(?:prevent|detect)\b",
            r"\b(?:fairly|reasonably)\s+present\b",
            r"\b(?:in accordance with|pursuant to)\s+(?:gaap|ifrs|sec|pcaob)\b",
            r"\b(?:general|standard)\s+(?:risk|regulatory|legal)\b",
        ]

        for pattern in generic_patterns:
            if re.search(pattern, context_lower):
                return True

        return False

    def classify_keyword_context(self, keyword, context):
        if not context:
            return "normal"

        context_lower = context.lower()

        strong_signals = [
            "material weakness",
            "material misstatement",
            "restatement",
            "adverse opinion",
            "disclaimer of opinion",
            "substantial doubt",
            "going concern",
            "severe impact",
            "critical audit matter",
            "fraudulent activity",
            "illegal conduct",
            "accounting irregularities",
            "significant deficiency",
        ]

        for signal in strong_signals:
            if signal in context_lower:
                return "significant"

        medium_signals = [
            "investigation",
            "legal proceedings",
            "lawsuit",
            "regulatory inquiry",
            "impairment loss",
            "restructuring charge",
            "qualifying opinion",
            "qualified opinion",
            "non-recurring charge",
            "write-down",
            "special charge",
        ]

        for signal in medium_signals:
            if signal in context_lower:
                return "potential"

        if self.is_generic_disclosure(context):
            return "normal"

        if keyword in {"fraud", "investigation"} and "risk factor" in context_lower:
            return "normal"

        return "normal"

    # Create Standard Flag

    def create_flag(self, flag_type, severity, status, message, context, ai_result):

        return {
            "type": flag_type,
            "severity": severity,
            "status": status,
            "message": message,
            "evidence": context,
            "ai_analysis": ai_result,
            "ai_decision": self.get_ai_decision(ai_result),
            "ai_confidence": self.get_ai_confidence(ai_result),
        }

    def _evaluate_keyword(self, keyword, text, default_severity="Medium"):
        context = self.get_context(text, keyword)
        ai_result = self.ai_analysis(context)
        classification = self.classify_keyword_context(keyword, context)

        if classification == "normal":
            ai_decision = "No"
            ai_confidence = "High"
            status = "Normal Context"
            severity = "Low"
            message = f"'{keyword}' language appears in a normal disclosure or generic context."
        elif classification == "potential":
            ai_decision = "Yes"
            ai_confidence = self.get_ai_confidence(ai_result) or "Medium"
            status = "Potential Concern"
            severity = default_severity
            message = f"'{keyword}' language appears to describe a possible company-specific concern."
        else:
            ai_decision = "Yes"
            ai_confidence = self.get_ai_confidence(ai_result) or "High"
            status = "Significant Issue"
            severity = "High"
            message = f"'{keyword}' language appears to reflect a material company-specific issue."

        return {
            "type": keyword.replace("_", " ").title(),
            "severity": severity,
            "status": status,
            "message": message,
            "evidence": context,
            "ai_analysis": ai_result,
            "ai_decision": ai_decision,
            "ai_confidence": ai_confidence,
        }

    # Analyze Financial Document

    def analyze(self, text, extracted_metrics=None):

        red_flags = []

        text_lower = text.lower()

        # 1. Auditor Qualification

        unqualified_opinion = re.search(
            r"\bunqualified\s+(?:audit\s+)?opinion\b", text_lower
        )

        qualified_opinion = re.search(
            r"\bqualified\s+(?:audit\s+)?opinion\b", text_lower
        )

        adverse_opinion = re.search(r"\badverse\s+opinion\b", text_lower)

        disclaimer_opinion = re.search(r"\bdisclaimer\s+of\s+opinion\b", text_lower)

        if qualified_opinion and not unqualified_opinion:
            context = self.get_context(text, "qualified opinion")
            ai_result = self.ai_analysis(context)
            red_flags.append(
                self.create_flag(
                    "Auditor Qualification",
                    "High",
                    "Significant Issue",
                    "Qualified auditor opinion detected.",
                    context,
                    ai_result,
                )
            )

        if adverse_opinion:
            context = self.get_context(text, "adverse opinion")
            ai_result = self.ai_analysis(context)
            red_flags.append(
                self.create_flag(
                    "Auditor Qualification",
                    "High",
                    "Significant Issue",
                    "Adverse auditor opinion detected.",
                    context,
                    ai_result,
                )
            )

        if disclaimer_opinion:
            context = self.get_context(text, "disclaimer of opinion")
            ai_result = self.ai_analysis(context)
            red_flags.append(
                self.create_flag(
                    "Auditor Qualification",
                    "High",
                    "Significant Issue",
                    "Auditor disclaimer of opinion detected.",
                    context,
                    ai_result,
                )
            )

        # 2. Going Concern

        if "going concern" in text_lower:
            context = self.get_context(text, "going concern")
            ai_result = self.ai_analysis(context)
            classification = self.classify_keyword_context("going concern", context)
            if classification == "normal":
                status = "Normal Context"
                severity = "Low"
                message = "Going concern language is generic and not a confirmed issue."
                ai_decision = "No"
            elif classification == "potential":
                status = "Potential Concern"
                severity = "Medium"
                message = "Going concern language indicates a possible financial strain."
                ai_decision = "Yes"
            else:
                status = "Significant Issue"
                severity = "High"
                message = "Going concern language suggests a material financial issue."
                ai_decision = "Yes"

            red_flags.append({
                "type": "Going Concern",
                "severity": severity,
                "status": status,
                "message": message,
                "evidence": context,
                "ai_analysis": ai_result,
                "ai_decision": ai_decision,
                "ai_confidence": self.get_ai_confidence(ai_result) or "Medium",
            })

        # 3. Material Misstatement

        if "material misstatement" in text_lower:
            context = self.get_context(text, "material misstatement")
            ai_result = self.ai_analysis(context)
            classification = self.classify_keyword_context("material misstatement", context)
            if classification == "normal":
                status = "Normal Context"
                severity = "Low"
                decision = "No"
                message = "Material misstatement language is generic and not a confirmed error."
            else:
                status = "Significant Issue"
                severity = "High"
                decision = "Yes"
                message = "Material misstatement language suggests a materially important issue."

            red_flags.append({
                "type": "Material Misstatement",
                "severity": severity,
                "status": status,
                "message": message,
                "evidence": context,
                "ai_analysis": ai_result,
                "ai_decision": decision,
                "ai_confidence": self.get_ai_confidence(ai_result) or "High",
            })

        # 4. Impairment Loss

        if "impairment loss" in text_lower:
            red_flags.append(self._evaluate_keyword("impairment loss", text, default_severity="Medium"))

        # 5. Restructuring Charge

        if "restructuring charge" in text_lower:
            red_flags.append(self._evaluate_keyword("restructuring charge", text, default_severity="Medium"))

        # 6. Fraud / Investigation

        for keyword in ["fraud", "investigation"]:
            if keyword not in text_lower:
                continue
            red_flags.append(self._evaluate_keyword(keyword, text, default_severity="Medium"))

        # 7. Low Profit Margin

        if extracted_metrics:
            ratios = extracted_metrics.get("financial_ratios", {})
            profit_margin = ratios.get("profit_margin")
            if profit_margin is not None and profit_margin < 5:
                red_flags.append(
                    {
                        "type": "Low Profit Margin",
                        "severity": "Medium",
                        "status": "Potential Concern",
                        "message": f"Profit margin is {profit_margin}%.",
                        "ai_decision": "Yes",
                        "ai_confidence": "Medium",
                    }
                )

        potential_red_flags = []
        review_items = []

        for flag in red_flags:
            decision = flag.get("ai_decision", "Unknown")
            if decision == "Yes":
                potential_red_flags.append(flag)
            else:
                review_items.append(flag)

        return {
            "detected_items": len(red_flags),
            "potential_red_flags": len(potential_red_flags),
            "review_items": len(review_items),
            "red_flags": red_flags,
            "potential_red_flag_items": potential_red_flags,
            "review_items_list": review_items,
        }
