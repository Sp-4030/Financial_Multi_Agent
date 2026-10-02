from agents.research_agent import ResearchAgent


# ==========================================
# Create Research Agent
# ==========================================

agent = ResearchAgent()


# ==========================================
# Test Multi-Part Financial Query
# ==========================================

query = """
1. What was EPAM's revenue in 2025?
2. What was its net income?
3. What was the profit margin?
4. Was there any restructuring-related charge?
"""


# ==========================================
# Run Research Agent
# ==========================================

result = agent.research(
    query,
    top_k=5
)


# ==========================================
# Display Result
# ==========================================

print("\n" + "=" * 70)
print("RESEARCH AGENT RESULT")
print("=" * 70)


print(
    "\nTotal Questions:",
    result["total_questions"]
)


# ==========================================
# Display Each Answer
# ==========================================

for item in result["results"]:

    print("\n")
    print("=" * 70)

    print(
        "Question",
        item["question_number"]
    )

    print("=" * 70)

    print(
        item["question"]
    )


    print("\nAnswer:")
    print("-" * 70)

    print(
        item["answer"]
    )


    print("\nRetrieved Chunks:")

    print(
        item["retrieved_chunks"]
    )


    print("\nSources:")

    for source in item["sources"]:

        print(
            f"- {source['source']} | "
            f"{source['company']} | "
            f"{source['document']} | "
            f"Chunk {source['chunk']}"
        )


# ==========================================
# Completed
# ==========================================

print("\n" + "=" * 70)
print("RESEARCH TEST COMPLETED")
print("=" * 70)