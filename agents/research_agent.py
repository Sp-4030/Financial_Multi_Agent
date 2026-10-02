import re
import ollama
import chromadb


class ResearchAgent:

    def __init__(self):

        # ==========================================
        # Ollama Model
        # ==========================================

        self.model = "llama3.2:latest"


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
        candidates = []
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
        for token in cleaned.split():
            if len(token) > 2 and token.lower() not in {"what", "when", "where", "which", "company", "financial", "revenue", "net", "income", "profit", "margin", "charge", "was", "were", "its", "there", "any", "did", "the", "a", "an", "for", "in", "on"}:
                candidates.append(token.title())
        return list(dict.fromkeys(candidates))

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

        if not retrieved and company_hints:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
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
8. Cite every important factual statement using:
   [Source 1], [Source 2], etc.
9. Do not create fake source numbers.
10. Use multiple sources when they are relevant.
11. If sources disagree, clearly mention the difference.
12. Do not treat generic risk disclosures as confirmed
    company-specific events.
13. Do not claim fraud, wrongdoing, or investigation
    unless the source specifically provides evidence.

USER QUESTION:

{question}


DOCUMENT CONTEXT:

{context}


ANSWER:
"""


        # ==========================================
        # Ollama
        # ==========================================

        try:

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )


            answer = response[
                "message"
            ][
                "content"
            ]


        except Exception as e:

            answer = (
                f"Research Agent error: {str(e)}"
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
                )

            })


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
            )

        }