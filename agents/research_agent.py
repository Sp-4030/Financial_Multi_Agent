import logging
import os
import re
from difflib import SequenceMatcher
from typing import Callable

import chromadb
from agents.comparison_agent import ComparisonAgent
from agents.extraction_agent import ExtractionAgent
from agents.red_flag_agent import RedFlagAgent
from agents.report_agent import ReportAgent
from utils.gemini_client import generate_gemini_content, GeminiError
from utils.embeddings import create_embeddings
from utils.paths import VECTOR_DB_PATH

logger = logging.getLogger(__name__)


class _OllamaCompat:
    @staticmethod
    def chat(model, messages, **kwargs):
        prompt = messages[0]["content"] if messages else ""
        text = generate_gemini_content(prompt=prompt, model=model)
        return {"message": {"content": text}}


ollama = _OllamaCompat()


class ResearchAgent:

    def __init__(self, model=None, collection=None, embedder=None):

        # ==========================================
        # Google Gemini Model
        # ==========================================

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


        # ==========================================
        # ChromaDB
        # ==========================================

        self.client = None
        if collection is None:
            self.client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = self.client.get_or_create_collection(
                name="financial_documents"
            )
        self.collection = collection
        self.embedder = embedder or create_embeddings
        self.extraction_agent = ExtractionAgent()
        self.comparison_agent = ComparisonAgent(collection=self.collection)
        self.red_flag_agent = RedFlagAgent(model=self.model)
        self.report_agent = ReportAgent()

    MAX_QUERY_LENGTH = 5000

    FINANCIAL_CONCEPTS = {
        "eps": (
            "Earnings per share (EPS) is net income attributable to ordinary "
            "shareholders divided by the weighted-average number of ordinary "
            "shares. It indicates earnings on a per-share basis; it is not the "
            "same as the share price."
        ),
        "revenue": (
            "Revenue is the income a business earns from selling goods or "
            "providing services before subtracting operating costs, interest, "
            "and taxes."
        ),
        "net profit": (
            "Net profit is the amount left after expenses, interest, and taxes "
            "are deducted from income for the reporting period."
        ),
        "operating profit": (
            "Operating profit is profit from the company's core operations "
            "after operating expenses, before interest and income taxes."
        ),
        "profit margin": (
            "Net profit margin measures how much net profit is earned per unit "
            "of revenue. Formula: net profit / revenue x 100%."
        ),
        "roe": (
            "Return on equity (ROE) measures profit relative to shareholders' "
            "equity. A common formula is net income / average shareholders' "
            "equity x 100%; using ending equity instead is an approximation."
        ),
        "roa": (
            "Return on assets (ROA) measures profit relative to assets. A "
            "common formula is net income / average total assets x 100%; using "
            "ending assets instead is an approximation."
        ),
        "debt": (
            "Debt is money a company has borrowed and is obligated to repay, "
            "usually with interest. A report may distinguish current "
            "borrowings from long-term debt."
        ),
        "assets": (
            "Assets are resources controlled by a company that are expected to "
            "provide future economic benefit, such as cash, receivables, "
            "property, and equipment."
        ),
        "liabilities": (
            "Liabilities are a company's present obligations, such as loans, "
            "payables, and accrued expenses."
        ),
        "equity": (
            "Shareholders' equity is the residual interest in a company's "
            "assets after liabilities are deducted."
        ),
        "ebitda": (
            "EBITDA means earnings before interest, taxes, depreciation, and "
            "amortization. It is a non-GAAP performance measure and does not "
            "represent cash flow or net income."
        ),
        "dividend": (
            "A dividend is a distribution of a company's earnings or reserves "
            "to its shareholders, subject to the company's policy and applicable "
            "rules."
        ),
        "liquidity": (
            "Liquidity describes how readily a company can meet near-term "
            "obligations using cash or assets that can be converted to cash."
        ),
        "solvency": (
            "Solvency describes a company's ability to meet its longer-term "
            "financial obligations."
        ),
    }

    @staticmethod
    def _contains_term(query, terms):
        words = re.findall(r"[a-z0-9]+", query.casefold())
        normalized = " ".join(words)
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", normalized):
                return True
            if len(term) >= 5 and any(
                SequenceMatcher(None, term, word).ratio() >= 0.84
                for word in words
                if abs(len(term) - len(word)) <= 2
            ):
                return True
        return False

    def classify_query(self, query, conversation_history=None):
        """Classify intents using lightweight rules; no report data is inferred."""
        if not isinstance(query, str):
            return {
                "category": "invalid_input",
                "tasks": [],
                "follow_up": False,
                "message": "Question must be text.",
            }
        clean_query = query.strip()
        if not clean_query:
            return {
                "category": "invalid_input",
                "tasks": [],
                "follow_up": False,
                "message": "Enter a financial question to get started.",
            }
        if len(clean_query) > self.MAX_QUERY_LENGTH:
            return {
                "category": "invalid_input",
                "tasks": [],
                "follow_up": False,
                "message": (
                    f"Question is too long (limit: {self.MAX_QUERY_LENGTH} characters)."
                ),
            }

        words = clean_query.casefold()
        tasks = []
        intent_terms = (
            ("comparison", ("compare", "comparison", "versus", "vs", "higher", "lower")),
            (
                "trend_analysis",
                (
                    "trend", "increase", "decrease", "grew", "declined",
                    "year over year", "across available years",
                    "over available years", "over time",
                ),
            ),
            (
                "red_flag_analysis",
                (
                    "red flag", "red flags", "risk", "risks", "going concern",
                    "auditor", "qualified opinion",
                ),
            ),
            ("financial_calculation", ("calculate", "compute", "work out", "formula")),
            (
                "report_generation",
                (
                    "generate report", "generate a report", "generate complete report",
                    "create report", "create a report", "complete report",
                    "financial report",
                ),
            ),
            ("document_summary", ("summarize", "summarise", "summary")),
            ("financial_extraction", ("extract", "key metrics", "financial metrics", "all metrics")),
        )
        for task, terms in intent_terms:
            if self._contains_term(words, terms):
                tasks.append(task)

        concepts_mentioned = [
            concept
            for concept in self.FINANCIAL_CONCEPTS
            if self._contains_term(words, (concept,))
        ]
        has_financial_concept = self._contains_term(
            words,
            tuple(self.FINANCIAL_CONCEPTS)
            + ("financial ratio", "balance sheet", "cash flow", "income statement"),
        )
        asks_definition = self._contains_term(
            words, ("what is", "what are", "explain", "define", "meaning", "in simple words")
        )
        if has_financial_concept and asks_definition:
            tasks.append("financial_concept")

        known_companies = self.extract_company_names(clean_query)
        if not tasks and (known_companies or has_financial_concept):
            tasks.append("document_research")
        if not tasks and self._contains_term(
            words,
            (
                "financial", "finance", "company", "business", "investment",
                "stock", "accounting", "inflation", "interest rate",
                "borrowing", "loan", "credit", "economy", "market", "tax",
                "budget", "currency", "bank", "capital", "cash",
            ),
        ):
            tasks.append("general_financial_question")
        if not tasks:
            tasks.append("unsupported_question")

        history = conversation_history if isinstance(conversation_history, list) else []
        is_follow_up = bool(history) and self._contains_term(
            words,
            ("it", "its", "they", "them", "that", "those", "there", "what about", "and"),
        )
        if is_follow_up and "document_research" not in tasks:
            tasks.append("document_research")

        unique_tasks = list(dict.fromkeys(tasks))
        parts = self.split_query(clean_query)
        multi_part = (
            len(unique_tasks) > 1
            or len(parts) > 1
            or (asks_definition and len(concepts_mentioned) > 1)
        )
        category = "multi_part_question" if multi_part else unique_tasks[0]
        return {
            "category": category,
            "tasks": unique_tasks,
            "follow_up": is_follow_up,
        }

    def _concept_answer(self, query):
        normalized_query = query.casefold()
        answers = []
        for concept, answer in self.FINANCIAL_CONCEPTS.items():
            aliases = {
                "eps": ("eps", "earnings per share"),
                "roe": ("roe", "return on equity"),
                "roa": ("roa", "return on assets"),
                "net profit": ("net profit", "net income"),
            }.get(concept, (concept,))
            if any(self._contains_term(normalized_query, (alias,)) for alias in aliases):
                answers.append(f"**{concept.upper()}**: {answer}")
        if answers:
            return "\n\n".join(dict.fromkeys(answers))
        if "financial ratio" in normalized_query:
            return (
                "A financial ratio compares figures from financial statements "
                "to help assess performance, liquidity, leverage, or efficiency. "
                "The right interpretation depends on the company, period, and "
                "accounting definitions."
            )
        if "balance sheet" in normalized_query:
            return (
                "A balance sheet reports a company's assets, liabilities, and "
                "shareholders' equity at a point in time. It follows the "
                "relationship: assets = liabilities + equity."
            )
        if "cash flow" in normalized_query:
            return (
                "A cash-flow statement reports cash generated and used during a "
                "period, typically split into operating, investing, and financing "
                "activities."
            )
        if "income statement" in normalized_query:
            return (
                "An income statement summarizes revenue, expenses, and profit or "
                "loss over a reporting period."
            )
        return None

    def _answer_general_financial_question(self, query):
        prompt = (
            "Answer this general educational finance question clearly and "
            "concisely. Do not make company-specific claims, invent current "
            "market data, or give personalized investment advice. State when "
            "definitions vary by accounting standard or jurisdiction.\n\n"
            f"Question: {query}"
        )
        try:
            answer = generate_gemini_content(prompt=prompt, model=self.model)
        except GeminiError as exc:
            logger.warning("General financial explanation unavailable: %s", exc)
            return (
                "I can answer general finance questions when the configured "
                "Gemini service is available. This request does not require "
                "company data; configure GEMINI_API_KEY or ask about one of the "
                "built-in financial concepts."
            )
        if not answer:
            return (
                "The configured language model returned no explanation. Please "
                "rephrase the general finance question."
            )
        return answer

    def _history_company(self, conversation_history):
        for message in reversed(conversation_history or []):
            content = message.get("content", "") if isinstance(message, dict) else ""
            companies = self.extract_company_names(content)
            if companies:
                return companies[0]
            for result in message.get("results", []) if isinstance(message, dict) else []:
                for source in result.get("sources", []) if isinstance(result, dict) else []:
                    company = source.get("company")
                    if company:
                        return str(company)
        return None

    @staticmethod
    def _numeric_value(value):
        if value is None:
            return None
        return ExtractionAgent().clean_number(str(value))

    @staticmethod
    def _explicit_unit_signature(value):
        value = str(value or "").casefold()
        currency = next(
            (
                name
                for name, pattern in (
                    ("INR", r"\binr\b|\brs\.?\b|₹"),
                    ("USD", r"\busd\b|\$"),
                    ("EUR", r"\beur\b|€"),
                    ("GBP", r"\bgbp\b|£"),
                )
                if re.search(pattern, value)
            ),
            None,
        )
        scale = next(
            (
                name
                for name, pattern in (
                    ("crore", r"\bcrores?\b"),
                    ("lakh", r"\blakhs?\b"),
                    ("billion", r"\bbillions?\b|\bbn\b"),
                    ("million", r"\bmillions?\b|\bmn\b"),
                    ("thousand", r"\bthousands?\b"),
                )
                if re.search(pattern, value)
            ),
            None,
        )
        return (currency, scale) if currency and scale else None

    def _comparison_table(self, comparison, query):
        requested_metrics = [
            (key, label)
            for key, label in (
                ("revenue", "Revenue"),
                ("net_profit", "Net profit"),
                ("operating_profit", "Operating profit"),
                ("eps", "EPS"),
                ("debt", "Debt"),
                ("total_assets", "Total assets"),
                ("total_liabilities", "Total liabilities"),
            )
            if self._contains_term(query.casefold(), (label.casefold(),))
        ]
        if not requested_metrics:
            requested_metrics = [
                ("revenue", "Revenue"),
                ("net_profit", "Net profit"),
                ("eps", "EPS"),
                ("debt", "Debt"),
            ]
        rows = []
        for document in comparison.get("documents", []):
            metrics = document.get("metrics", {})
            rows.append(
                {
                    "company": document.get("company", "Unknown"),
                    "financial_year": document.get("financial_year") or "N/A",
                    "document": document.get("document", "Unknown"),
                    "source": document.get("document", "Unknown"),
                    "units": "Not separately identified",
                    **{
                        label: metrics.get(key) or "N/A"
                        for key, label in requested_metrics
                    },
                }
            )
        return rows, [label for _, label in requested_metrics]

    def handle_query(
        self,
        query,
        top_k=5,
        company=None,
        document_id=None,
        conversation_history=None,
        progress_callback: Callable[[int, str], None] | None = None,
    ):
        """Route educational and document-backed requests through existing agents."""

        def report_progress(step, state):
            if progress_callback is not None:
                progress_callback(step, state)

        report_progress(1, "running")
        classification = self.classify_query(query, conversation_history)
        if classification["category"] == "invalid_input":
            report_progress(1, "complete")
            for step in (2, 3, 4):
                report_progress(step, "skipped")
            report_progress(5, "running")
            report_progress(5, "complete")
            return {
                "query": query if isinstance(query, str) else "",
                **classification,
                "answer": classification["message"],
                "results": [],
                "sources": [],
            }
        if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 20:
            message = "Retrieval count must be an integer from 1 to 20."
            report_progress(1, "complete")
            for step in (2, 3, 4):
                report_progress(step, "skipped")
            report_progress(5, "running")
            report_progress(5, "complete")
            return {
                "query": query,
                "category": "invalid_input",
                "tasks": [],
                "follow_up": False,
                "message": message,
                "answer": message,
                "results": [],
                "sources": [],
            }
        history = conversation_history if isinstance(conversation_history, list) else []
        task_names = set(classification["tasks"])
        effective_company = company
        if classification["follow_up"] and not self.extract_company_names(query):
            effective_company = self._history_company(history) or effective_company

        document_tasks = task_names.intersection(
            {
                "document_research",
                "financial_extraction",
                "trend_analysis",
                "red_flag_analysis",
                "document_summary",
                "report_generation",
                "financial_calculation",
                "comparison",
            }
        )
        report_progress(1, "complete")
        if document_tasks:
            report_progress(2, "running")
            indexed_documents = self.comparison_agent.list_indexed_documents()
        else:
            for step in (2, 3, 4):
                report_progress(step, "skipped")
            indexed_documents = []
        indexed_companies = sorted(
            {
                str(item.get("company", "")).strip()
                for item in indexed_documents
                if item.get("company")
            },
            key=str.casefold,
        )
        mentioned_companies = (
            self._company_candidates(query) if document_tasks else []
        )
        if not mentioned_companies and effective_company:
            mentioned_companies = [
                name for name in indexed_companies
                if name.casefold() == effective_company.casefold()
            ]
        if classification["follow_up"] and not mentioned_companies and effective_company:
            mentioned_companies = [effective_company]
        if document_tasks:
            report_progress(2, "complete")

        result = {
            "query": query,
            "category": classification["category"],
            "tasks": classification["tasks"],
            "follow_up": classification["follow_up"],
            "results": [],
            "sources": [],
        }
        sections = []
        source_keys = set()
        research_results = []
        red_flag_reports = []

        def add_sources(sources):
            for source in sources:
                key = (
                    source.get("document_id"),
                    source.get("document"),
                    source.get("chunk"),
                )
                if key not in source_keys:
                    source_keys.add(key)
                    result["sources"].append(source)

        concept_answer = self._concept_answer(query)
        if "financial_concept" in task_names and concept_answer:
            sections.append(f"**Financial concept**\n{concept_answer}")

        if document_tasks and not indexed_documents:
            report_progress(3, "skipped")
            report_progress(4, "skipped")
            no_docs = (
                "There are no indexed reports yet. Upload and index the relevant "
                "company PDF before requesting company-specific figures, risks, "
                "comparisons, or summaries."
            )
            sections.append(no_docs)
            result["results"].append(
                {"question": query, "answer": no_docs, "sources": [], "retrieved_chunks": 0}
            )
        elif document_tasks:
            requested_names = self._requested_comparison_companies(
                query, mentioned_companies, indexed_companies
            ) if "comparison" in task_names else mentioned_companies
            target_names = requested_names or mentioned_companies
            if not target_names and effective_company:
                target_names = [effective_company]

            missing_companies = [
                name for name in target_names
                if not any(name.casefold() == indexed.casefold() for indexed in indexed_companies)
            ]
            if missing_companies:
                message = (
                    "No indexed report was found for "
                    + ", ".join(missing_companies)
                    + ". Upload and index that company's report to include it."
                )
                sections.append(message)
                result["companies_not_indexed"] = missing_companies

            report_progress(3, "running")
            comparison = self.comparison_agent.compare(
                [name for name in target_names if name not in missing_companies]
                if target_names
                else None
            )
            result["comparison"] = comparison if "comparison" in task_names else None

            if "comparison" in task_names:
                table, metric_columns = self._comparison_table(comparison, query)
                result["comparison_table"] = {
                    "columns": [
                        "company", "financial_year", *metric_columns,
                        "units", "source",
                    ],
                    "rows": table,
                }
                if table:
                    sections.append(
                        "Comparison uses values extracted from each company's indexed "
                        "document. Reporting years may differ; N/A means the metric "
                        "was not extracted. Review the source documents before drawing "
                        "period-adjusted conclusions."
                    )
                if self._contains_term(
                    query.casefold(),
                    ("higher", "lower", "which company", "who had more"),
                ):
                    findings = []
                    if len(metric_columns) == 1:
                        metric = metric_columns[0]
                        years = {
                            row["financial_year"]
                            for row in table
                            if row["financial_year"] != "N/A"
                        }
                        companies_by_year = {}
                        for row in table:
                            value = self._numeric_value(row.get(metric))
                            if value is not None and row["financial_year"] != "N/A":
                                companies_by_year.setdefault(
                                    row["financial_year"], []
                                ).append((row["company"], value))
                        comparable = next(
                            (
                                (year, values)
                                for year, values in sorted(companies_by_year.items(), reverse=True)
                                if len(values) >= 2
                            ),
                            None,
                        )
                        same_explicit_unit = False
                        if comparable:
                            comparison_year, values = comparable
                            comparison_companies = {name for name, _ in values}
                            signatures = {
                                self._explicit_unit_signature(
                                    row.get(metric)
                                )
                                for row in table
                                if row["financial_year"] == comparison_year
                                and row["company"] in comparison_companies
                                and row.get(metric) != "N/A"
                            }
                            same_explicit_unit = (
                                len(signatures) == 1 and None not in signatures
                            )
                        if comparable and same_explicit_unit:
                            year, values = comparable
                            highest = max(values, key=lambda item: item[1])
                            findings.append(
                                f"For {metric} in FY {year}, {highest[0]} has the "
                                "higher extracted value among the indexed reports."
                            )
                        elif len(years) > 1 or comparable:
                            findings.append(
                                "A fair ranking is unavailable because reporting "
                                "periods differ or the extracted values do not carry "
                                "matching explicit currency and scale information."
                            )
                        else:
                            findings.append(
                                "A fair ranking is unavailable because comparable "
                                "numeric values were not extracted."
                            )
                    result["comparison_conclusions"] = findings
                    if findings:
                        sections.extend(findings)
                elif not missing_companies:
                    sections.append(
                        "No indexed documents matched the requested company names."
                    )

            selected_docs = [
                doc for doc in comparison.get("documents", [])
                if not document_id or doc.get("document_id") == document_id
            ]
            if not selected_docs and not target_names and indexed_documents:
                selected_docs = self.comparison_agent.get_company_documents(
                    str(indexed_documents[-1].get("company", ""))
                )
            if "financial_extraction" in task_names:
                extracted = [
                    {
                        "company": doc["company"],
                        "financial_year": doc.get("financial_year") or "N/A",
                        "document": doc["document"],
                        "metrics": doc["metrics"],
                    }
                    for doc in selected_docs
                ]
                result["extracted_metrics"] = extracted
                sections.append(
                    "Extracted metrics are available in the structured result; "
                    "missing values are left as N/A."
                )

            if "trend_analysis" in task_names:
                trend_rows, _ = self._comparison_table(
                    {"documents": selected_docs}, query
                )
                trend_metric = (
                    "Revenue" if self._contains_term(query.casefold(), ("revenue",))
                    else "Net profit" if self._contains_term(query.casefold(), ("net profit", "profit"))
                    else "Revenue"
                )
                grouped_trends = {}
                for row in trend_rows:
                    value = self._numeric_value(row.get(trend_metric))
                    if value is not None and row["financial_year"] != "N/A":
                        grouped_trends.setdefault(row["company"], []).append(
                            (row["financial_year"], value, row[trend_metric], row["source"])
                        )
                trend_comparisons = []
                for name, values in grouped_trends.items():
                    values.sort(key=lambda item: item[0])
                    for previous, current in zip(values, values[1:]):
                        direction = (
                            "increased" if current[1] > previous[1]
                            else "decreased" if current[1] < previous[1]
                            else "was unchanged"
                        )
                        trend_comparisons.append(
                            {
                                "company": name,
                                "metric": trend_metric,
                                "from_year": previous[0],
                                "from_value": previous[2],
                                "to_year": current[0],
                                "to_value": current[2],
                                "direction": direction,
                                "sources": [previous[3], current[3]],
                            }
                        )
                result["trend"] = {
                    "available_documents": trend_rows,
                    "comparisons": trend_comparisons,
                }
                if trend_comparisons:
                    sections.append(
                        "Year-over-year direction is calculated from the extracted "
                        "reported figures shown in the result; confirm units and "
                        "accounting comparability in the cited reports."
                    )
                else:
                    sections.append(
                        "Available year-by-year figures are listed in the result. "
                        "A trend is not inferred because at least two comparable "
                        "numeric years were not available."
                    )

            if "financial_calculation" in task_names:
                calculations = []
                calculation_specs = (
                    (
                        "Profit margin",
                        ("profit margin", "net margin", "margin"),
                        "net_profit",
                        "revenue",
                        "net profit / revenue x 100",
                    ),
                    (
                        "ROE",
                        ("roe", "return on equity"),
                        "net_profit",
                        "shareholders_equity",
                        "net profit / shareholders' equity x 100",
                    ),
                    (
                        "ROA",
                        ("roa", "return on assets"),
                        "net_profit",
                        "total_assets",
                        "net profit / total assets x 100",
                    ),
                    (
                        "Debt to assets",
                        ("debt to assets", "debt-to-assets"),
                        "debt",
                        "total_assets",
                        "debt / total assets x 100",
                    ),
                    (
                        "Liabilities to assets",
                        ("liabilities to assets", "liabilities-to-assets"),
                        "total_liabilities",
                        "total_assets",
                        "total liabilities / total assets x 100",
                    ),
                )
                requested_calculations = [
                    spec for spec in calculation_specs
                    if self._contains_term(query.casefold(), spec[1])
                ]
                for doc in selected_docs:
                    metrics = doc.get("metrics", {})
                    for label, _, numerator_key, denominator_key, formula in requested_calculations:
                        numerator_value = self._numeric_value(
                            metrics.get(numerator_key)
                        )
                        denominator_value = self._numeric_value(
                            metrics.get(denominator_key)
                        )
                        if (
                            numerator_value is not None
                            and denominator_value not in (None, 0)
                        ):
                            calculations.append(
                                {
                                    "company": doc["company"],
                                    "financial_year": doc.get("financial_year") or "N/A",
                                    "metric": label,
                                    "formula": formula,
                                    "inputs": {
                                        numerator_key: metrics.get(numerator_key),
                                        denominator_key: metrics.get(denominator_key),
                                    },
                                    "result_percent": round(
                                        numerator_value / denominator_value * 100, 2
                                    ),
                                    "source": doc["document"],
                                }
                            )
                result["calculations"] = calculations
                if calculations:
                    sections.append(
                        "Calculations use extracted report figures; formulas, inputs, "
                        "periods, and source documents are included in the result."
                    )
                elif not requested_calculations:
                    sections.append(
                        "Specify a supported ratio to calculate: profit margin, ROE, "
                        "ROA, debt to assets, or liabilities to assets."
                    )
                else:
                    sections.append(
                        "I could not calculate the requested ratio because its "
                        "verified input figures were unavailable or incomplete."
                    )

            report_progress(3, "complete")
            research_needed = task_names.intersection(
                {"document_research", "red_flag_analysis", "document_summary"}
            )
            if selected_docs or research_needed:
                report_progress(4, "running")
                if selected_docs and task_names.intersection(
                    {
                        "comparison",
                        "financial_extraction",
                        "trend_analysis",
                        "financial_calculation",
                        "report_generation",
                    }
                ):
                    for doc in selected_docs:
                        add_sources(
                            [
                                {
                                    "source": f"Source {len(result['sources']) + 1}",
                                    "company": doc["company"],
                                    "document": doc["document"],
                                    "chunk": "Extracted document metrics",
                                    "document_id": doc["document_id"],
                                }
                            ]
                        )
            if research_needed:
                research_questions = self.split_query(query)
                if not research_questions:
                    research_questions = [query]
                for question_number, research_question in enumerate(
                    research_questions, start=1
                ):
                    companies_for_question = self._company_candidates(
                        research_question
                    )
                    if not companies_for_question and effective_company:
                        companies_for_question = [effective_company]
                    per_company = companies_for_question or [None]
                    for target_company in per_company:
                        scoped_company = target_company or effective_company
                        search_query = research_question
                        if target_company and len(per_company) > 1:
                            search_query = f"{target_company}: {research_question}"
                        retrieved = []
                        try:
                            retrieved = self.retrieve(
                                search_query,
                                top_k=top_k,
                                company=scoped_company,
                                document_id=document_id,
                            )
                            if not retrieved:
                                requested_scope = (
                                    f" for {scoped_company}" if scoped_company else ""
                                )
                                answer_data = {
                                    "answer": (
                                        "No relevant evidence was retrieved"
                                        f"{requested_scope} from the selected indexed "
                                        "reports. Check the company/document selection "
                                        "or upload the report containing the requested fact."
                                    ),
                                    "sources": [],
                                }
                            else:
                                answer_data = self.generate_answer(
                                    search_query, retrieved
                                )
                        except GeminiError as exc:
                            logger.warning(
                                "Research LLM unavailable; returning retrieved evidence: %s",
                                exc,
                            )
                            answer_data = self._evidence_fallback(
                                retrieved, str(exc)
                            )
                        evidence_result = {
                            "question": research_question,
                            "answer": answer_data["answer"],
                            "sources": answer_data["sources"],
                            "retrieved_chunks": len(retrieved),
                            "company": target_company,
                        }
                        if len(research_questions) > 1:
                            evidence_result["question_number"] = question_number
                        research_results.append(evidence_result)
                        add_sources(answer_data["sources"])

                result["results"] = research_results
                if research_results:
                    sections.extend(item["answer"] for item in research_results)
                else:
                    sections.append("No relevant evidence was retrieved.")

            if "red_flag_analysis" in task_names or "report_generation" in task_names:
                for doc in selected_docs:
                    chunks = self.collection.get(
                        include=["documents", "metadatas"],
                        where={"document_id": doc["document_id"]},
                    )
                    texts = chunks.get("documents") or []
                    metadata_rows = chunks.get("metadatas") or []
                    text = "\n".join(str(item) for item in texts if item)
                    risk = self.red_flag_agent.analyze(text, doc.get("metrics", {}))
                    risk_sources = [
                        {
                            "source": f"Source {index}",
                            "company": (metadata_rows[index] or {}).get("company", doc["company"]),
                            "document": (metadata_rows[index] or {}).get("document_name", doc["document"]),
                            "chunk": (metadata_rows[index] or {}).get("chunk_number", "Unknown"),
                            "document_id": doc["document_id"],
                        }
                        for index in range(len(texts))
                    ]
                    add_sources(risk_sources)
                    red_flag_reports.append(
                        {
                            "company": doc["company"],
                            "financial_year": doc.get("financial_year") or "N/A",
                            "document": doc["document"],
                            "findings": risk.get("potential_red_flag_items", []),
                            "review_items": risk.get("review_items_list", []),
                        }
                    )
                result["red_flag_analysis"] = red_flag_reports
                if red_flag_reports and any(row["findings"] for row in red_flag_reports):
                    sections.append(
                        "Potential risk findings are listed with supporting document "
                        "evidence. These automated findings are not determinations of "
                        "fraud or legal violations."
                    )
                elif selected_docs and "red_flag_analysis" in task_names:
                    sections.append(
                        "The automated review found no potential red flags in the "
                        "available evidence; this does not establish that no risks exist."
                    )

            if selected_docs or research_needed:
                report_progress(4, "complete")
            else:
                report_progress(4, "skipped")

            if "report_generation" in task_names:
                report_progress(5, "running")
            if "report_generation" in task_names:
                if selected_docs:
                    primary = selected_docs[0]
                    report_metrics = dict(primary.get("metrics", {}))
                    report_metrics["company"] = primary.get("company")
                    report = self.report_agent.generate(
                        report_metrics,
                        red_flags={
                            "potential_red_flag_items": [
                                finding
                                for row in red_flag_reports
                                for finding in row["findings"]
                            ],
                            "red_flags": [
                                finding
                                for row in red_flag_reports
                                for finding in (
                                    row["findings"] + row["review_items"]
                                )
                            ],
                        },
                        document_name=primary.get("document", "Source document"),
                        comparison={"documents": selected_docs},
                        research_findings=research_results,
                        sources=result["sources"],
                    )
                    result["report"] = report
                    sections.append(report["executive_summary"])
                else:
                    sections.append(
                        "A report cannot be generated until a matching indexed report "
                        "is available."
                    )

        if not document_tasks or not indexed_documents or "report_generation" not in task_names:
            report_progress(5, "running")
        if "general_financial_question" in task_names:
            general_answer = self._answer_general_financial_question(query)
            result["general_answer"] = general_answer
            sections.append(general_answer)
        if "unsupported_question" in task_names:
            sections.append(
                "This system is designed for financial concepts and analysis of "
                "indexed financial reports. I can’t reliably answer this unrelated "
                "question; please ask about a financial topic or an indexed report."
            )

        if classification["follow_up"] and effective_company:
            result["resolved_company"] = effective_company
        result["answer"] = "\n\n".join(dict.fromkeys(section for section in sections if section))
        if not result["answer"]:
            result["answer"] = (
                "I could not determine the requested analysis. Please clarify the "
                "financial question or select an analysis type."
            )
        report_progress(5, "complete")
        return result

    def _requested_comparison_companies(self, query, mentioned, indexed):
        if len(mentioned) >= 2:
            return mentioned
        # Capture arbitrary names in natural forms such as "compare A and B";
        # exact indexed-name matches are resolved first and never hardcoded.
        match = re.search(
            r"\b(?:compare|comparison of)\s+(.+?)\s+(?:and|vs\.?|versus|with)\s+"
            r"(.+?)(?:[?.!,;]|$)",
            query,
            re.IGNORECASE,
        )
        if not match:
            return mentioned
        candidates = [part.strip(" \t'\".,?!") for part in match.groups()]
        candidates = [
            re.sub(
                r"\b(?:revenue|net profit|profit|eps|roe|roa|debt|assets|"
                r"financial years?|available years?)\b.*$",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()
            for candidate in candidates
        ]
        candidates = [candidate for candidate in candidates if candidate]
        resolved = []
        for candidate in candidates:
            match_name = next(
                (name for name in indexed if name.casefold() == candidate.casefold()),
                candidate,
            )
            if match_name not in resolved:
                resolved.append(match_name)
        return resolved or mentioned

    def _company_candidates(self, query):
        matched = self.extract_company_names(query)
        if matched:
            return matched
        stop_words = {
            "what", "which", "where", "when", "why", "how", "did", "does",
            "is", "are", "was", "were", "explain", "define", "compare",
            "identify", "generate", "summarize", "summarise", "calculate",
            "extract", "show", "tell", "please", "latest", "available",
            "financial", "revenue", "profit", "income", "debt", "assets",
            "liabilities", "report", "company", "companies", "and", "vs",
            "versus", "with",
        }
        tokens = re.findall(r"\b[A-Z][A-Za-z0-9&.-]*(?:'s)?\b", query)
        candidates = []
        index = 0
        while index < len(tokens):
            token = tokens[index].removesuffix("'s")
            if token.casefold() in stop_words or token.upper().startswith("FY"):
                index += 1
                continue
            parts = [token]
            index += 1
            while index < len(tokens) and tokens[index].casefold() not in stop_words:
                parts.append(tokens[index].removesuffix("'s"))
                index += 1
            candidate = " ".join(parts).strip()
            if candidate and candidate.casefold() not in {
                item.casefold() for item in candidates
            }:
                candidates.append(candidate)
        return candidates

    @staticmethod
    def _evidence_fallback(retrieved_documents, reason):
        if not retrieved_documents:
            return {
                "answer": (
                    "No supporting passages were retrieved from indexed reports. "
                    f"Research generation is unavailable: {reason}"
                ),
                "sources": [],
            }
        sources = []
        excerpts = []
        for index, item in enumerate(retrieved_documents, start=1):
            metadata = item.get("metadata", {})
            source = {
                "source": f"Source {index}",
                "company": metadata.get("company", "Unknown"),
                "document": metadata.get("document_name", "Unknown"),
                "chunk": metadata.get("chunk_number", "Unknown"),
                "document_id": metadata.get("document_id"),
            }
            sources.append(source)
            excerpt = re.sub(r"\s+", " ", str(item.get("document", ""))).strip()
            if excerpt:
                excerpts.append(f"{excerpt[:1200]} [Source {index}]")
        return {
            "answer": (
                "The language model is unavailable, so here are the retrieved "
                "source passages without additional interpretation:\n"
                + "\n\n".join(excerpts)
            ),
            "sources": sources,
        }


    # ==========================================
    # Split Multi-Part Query
    # ==========================================

    def split_query(self, query):

        query = query.strip()

        if not query:
            return []

        # ------------------------------------------
        # Split numbered questions
        # Example:
        # 1. What is revenue?
        # 2. What is profit?
        # ------------------------------------------

        numbered_parts = re.split(
            r"(?:^|\n)\s*\d+[\.\)]\s+",
            query
        )

        numbered_parts = [
            part.strip()
            for part in numbered_parts
            if part.strip()
        ]

        if len(numbered_parts) > 1:
            return numbered_parts


        # ------------------------------------------
        # Split lines
        # ------------------------------------------

        line_parts = [
            line.strip()
            for line in query.split("\n")
            if line.strip()
        ]

        if len(line_parts) > 1:
            return line_parts


        # ------------------------------------------
        # Single question
        # ------------------------------------------

        return [query]


    # ==========================================
    # Extract Company Mentions
    # ==========================================

    def extract_company_names(self, query):
        stored_companies = {
            str(metadata.get("company", "")).strip()
            for metadata in (self.collection.get(include=["metadatas"]).get("metadatas") or [])
            if metadata and str(metadata.get("company", "")).strip()
        }
        query_lower = query.casefold()
        query_tokens = re.findall(r"[a-z0-9]+", query_lower)
        first_tokens = {}
        for company in stored_companies:
            first_token = company.split()[0].casefold() if company.split() else ""
            if len(first_token) >= 3:
                first_tokens.setdefault(first_token, []).append(company)
        return sorted(
            (
                company
                for company in stored_companies
                if re.search(
                    rf"(?<!\w){re.escape(company.casefold())}(?!\w)",
                    query_lower,
                )
                or (
                    len(first_tokens.get(company.split()[0].casefold(), [])) == 1
                    and any(
                        SequenceMatcher(
                            None,
                            company.split()[0].casefold(),
                            token,
                        ).ratio()
                        >= 0.84
                        for token in query_tokens
                        if abs(len(company.split()[0]) - len(token)) <= 2
                    )
                )
            ),
            key=len,
            reverse=True,
        )

    # ==========================================
    # Retrieve Documents
    # ==========================================

    def retrieve(
        self,
        query,
        top_k=5,
        company=None,
        document_id=None,
    ):

        if not query.strip():
            return []
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        collection_count = self.collection.count()
        if collection_count == 0:
            return []

        stored_companies = {
            str(metadata.get("company", "")).strip()
            for metadata in (self.collection.get(include=["metadatas"]).get("metadatas") or [])
            if metadata and str(metadata.get("company", "")).strip()
        }
        if company:
            exact_matches = [
                name for name in stored_companies
                if name.casefold() == company.casefold()
            ]
            if exact_matches:
                company_hints = exact_matches
            else:
                first_token_matches = [
                    name
                    for name in stored_companies
                    if name.split()
                    and name.split()[0].casefold() == company.casefold()
                ]
                company_hints = (
                    first_token_matches if len(first_token_matches) == 1 else []
                )
        else:
            company_hints = self.extract_company_names(query)
        if company and not company_hints:
            return []
        where_conditions = []
        if company_hints:
            where_conditions.append({"company": {"$in": company_hints}})
        if document_id:
            where_conditions.append({"document_id": document_id})
        where = None
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif where_conditions:
            where = {"$and": where_conditions}

        query_embedding = self.embedder([query])
        if hasattr(query_embedding, "tolist"):
            query_embedding = query_embedding.tolist()
        query_vector = query_embedding[0]
        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, collection_count),
            where=where,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved = []

        for i, document in enumerate(documents):
            metadata = {}
            if i < len(metadatas):
                metadata = metadatas[i] or {}

            distance = None
            if i < len(distances):
                distance = distances[i]

            retrieved.append({
                "document": document,
                "metadata": metadata,
                "distance": distance
            })

        return retrieved


    # ==========================================
    # Build Source Context
    # ==========================================

    def build_context(
        self,
        retrieved_documents
    ):

        if not retrieved_documents:

            return (
                "No relevant document context was found."
            )


        context_parts = []


        for index, item in enumerate(
            retrieved_documents,
            start=1
        ):

            document = item["document"]

            metadata = item["metadata"]


            company = metadata.get(
                "company",
                "Unknown"
            )

            document_name = metadata.get(
                "document_name",
                "Unknown"
            )

            chunk_number = metadata.get(
                "chunk_number",
                "Unknown"
            )


            source_block = f"""
[Source {index}]

Company: {company}

Document: {document_name}

Chunk: {chunk_number}

Content:
{document}
"""


            context_parts.append(
                source_block.strip()
            )


        return "\n\n".join(
            context_parts
        )


    # ==========================================
    # Generate Answer with Ollama
    # ==========================================

    def generate_answer(
        self,
        question,
        retrieved_documents
    ):

        if not retrieved_documents:

            return {
                "answer": (
                    "I could not find relevant information "
                    "in the indexed financial documents."
                ),
                "sources": []
            }


        context = self.build_context(
            retrieved_documents
        )


        # ==========================================
        # Prompt
        # ==========================================

        prompt = f"""
You are a financial research assistant.

Answer the user's question using ONLY the
provided document context.

IMPORTANT RULES:

1. Do not use outside knowledge.
2. Do not invent financial figures.
3. Do not assume information that is not present.
4. Use only information contained in the sources.
5. If the sources do not contain enough information,
   clearly say that the information is not available
   in the indexed documents.
6. Preserve the meaning of the source.
7. When giving financial numbers, keep the original
   number and unit/context when available.
8. Cite every factual sentence using:
   [Source 1], [Source 2], etc.
9. Do not create fake source numbers.
10. Use multiple sources when they are relevant.
11. If sources disagree, clearly mention the difference.
12. Do not treat generic risk disclosures as confirmed
    company-specific events.
13. Do not claim fraud, wrongdoing, or investigation
    unless the source specifically provides evidence.
14. MANDATORY CITATION RULE: Every single sentence or statement in your answer MUST be explicitly cited with [Source 1], [Source 2], etc. Do not include any introductory sentences, conversational greetings, markdown headers, or concluding remarks that lack a citation. If information is not found in the sources, cite the relevant sources stating it is not available.

USER QUESTION:

{question}


DOCUMENT CONTEXT:

{context}


ANSWER:
"""


        # ==========================================
        # Gemini / LLM Generation
        # ==========================================

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        if isinstance(response, dict) and "message" in response:
            answer = str(response["message"].get("content", "")).strip()
        elif isinstance(response, str):
            answer = response.strip()
        else:
            answer = str(response).strip()

        answer = re.sub(
            r"([.!?])\s*(\[Source\s+\d+\])",
            r" \2\1",
            answer,
            flags=re.IGNORECASE,
        )


        # ==========================================
        # Sources
        # ==========================================

        sources = []


        for index, item in enumerate(
            retrieved_documents,
            start=1
        ):

            metadata = item["metadata"]


            sources.append({

                "source": f"Source {index}",

                "company": metadata.get(
                    "company",
                    "Unknown"
                ),

                "document": metadata.get(
                    "document_name",
                    "Unknown"
                ),

                "chunk": metadata.get(
                    "chunk_number",
                    "Unknown"
                ),
                "document_id": metadata.get("document_id"),

            })

        citation_numbers = [
            int(number)
            for number in re.findall(r"\[Source\s+(\d+)\]", answer, re.IGNORECASE)
        ]
        answer_sentences = [
            sentence.strip(" -*\t")
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer)
            if sentence.strip(" -*\t")
        ]
        has_uncited_sentence = any(
            not re.search(r"\[Source\s+\d+\]", sentence, re.IGNORECASE)
            for sentence in answer_sentences
        )
        if not citation_numbers or has_uncited_sentence or any(
            number < 1 or number > len(sources) for number in citation_numbers
        ):
            fallback = self._evidence_fallback(
                retrieved_documents,
                "The generated response did not contain verifiable source citations.",
            )
            answer = fallback["answer"]

        return {

            "answer": answer,

            "sources": sources

        }


    # ==========================================
    # Research Single Question
    # ==========================================

    def research_question(
        self,
        question,
        top_k=5,
        company=None,
        document_id=None,
    ):

        retrieved_documents = self.retrieve(
            question,
            top_k=top_k,
            company=company,
            document_id=document_id,
        )


        result = self.generate_answer(
            question,
            retrieved_documents
        )


        return {

            "question": question,

            "answer": result["answer"],

            "sources": result["sources"],

            "retrieved_chunks": len(
                retrieved_documents
            )

        }


    # ==========================================
    # Research Multi-Part Query
    # ==========================================

    def research(
        self,
        query,
        top_k=5,
        company=None,
        document_id=None,
    ):

        questions = self.split_query(
            query
        )


        if not questions:

            return {

                "query": query,

                "questions": [],

                "results": [],

                "total_questions": 0

            }


        results = []


        for index, question in enumerate(
            questions,
            start=1
        ):

            result = self.research_question(
                question,
                top_k=top_k,
                company=company,
                document_id=document_id,
            )


            result["question_number"] = index


            results.append(
                result
            )


        return {

            "query": query,

            "questions": questions,

            "results": results,

            "total_questions": len(
                questions
            ),
            "retrieval_steps": [
                {
                    "step": item["question_number"],
                    "question": item["question"],
                    "retrieved_chunks": item["retrieved_chunks"],
                    "sources": item["sources"],
                }
                for item in results
            ]

        }