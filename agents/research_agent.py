import os
import re
import chromadb
from utils.gemini_client import generate_gemini_content, GeminiError


class _OllamaCompat:
    @staticmethod
    def chat(model, messages, **kwargs):
        prompt = messages[0]["content"] if messages else ""
        text = generate_gemini_content(prompt=prompt, model=model)
        return {"message": {"content": text}}


ollama = _OllamaCompat()


class ResearchAgent:

    def __init__(self, model=None):

        # ==========================================
        # Google Gemini Model
        # ==========================================

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


        # ==========================================
        # ChromaDB
        # ==========================================

        self.client = chromadb.PersistentClient(
            path="vector_db"
        )

        self.collection = self.client.get_or_create_collection(
            name="financial_documents"
        )


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
        return sorted(
            (
                company
                for company in stored_companies
                if company.casefold() in query_lower
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
        top_k=5
    ):

        if not query.strip():
            return []
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        company_hints = self.extract_company_names(query)

        filter_conditions = {}
        if company_hints:
            filter_conditions = {"company": {"$in": company_hints}}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_conditions if filter_conditions else None,
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
            answer = (
                "I couldn't produce a fully source-cited answer from the retrieved "
                "documents. Please refine the question or try again."
            )

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
        top_k=5
    ):

        retrieved_documents = self.retrieve(
            question,
            top_k=top_k
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
        top_k=5
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
                top_k=top_k
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