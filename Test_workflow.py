from pathlib import Path
from workflow.graph import financial_workflow


# ==========================================
# PDF PATH
# ==========================================

pdf_path = Path(r"C:\Users\Shantanu\Desktop\Reports\Epam.pdf")
if not pdf_path.exists():
    pdf_path = Path("data/seed_documents/Epam.pdf")
if not pdf_path.exists():
    pdf_path = Path("data/uploads/Epam.pdf")


# ==========================================
# INITIAL WORKFLOW STATE
# ==========================================

initial_state = {
    "pdf_path": str(pdf_path)
}


# ==========================================
# RUN MULTI-AGENT WORKFLOW
# ==========================================

result = financial_workflow.invoke(
    initial_state
)


# ==========================================
# DISPLAY WORKFLOW RESULT
# ==========================================

print("\n" + "=" * 60)
print("MULTI-AGENT WORKFLOW RESULT")
print("=" * 60)


# ==========================================
# DOCUMENT RESULT
# ==========================================

print("\nDocument Result:")
print("-" * 60)

print(
    result["document_result"]
)


# ==========================================
# EXTRACTION RESULT
# ==========================================

print("\nFinancial Metrics:")
print("-" * 60)

print(
    result["extracted_metrics"]
)


# ==========================================
# RED FLAG RESULT
# ==========================================

print("\nRed Flag Analysis:")
print("=" * 60)

red_flag_result = result["red_flag_result"]


# ==========================================
# SUMMARY
# ==========================================

print(
    "\nDetected Items:",
    red_flag_result["detected_items"]
)

print(
    "Potential Red Flags:",
    red_flag_result["potential_red_flags"]
)

print(
    "Review / Normal Context:",
    red_flag_result["review_items"]
)


# ==========================================
# ALL DETECTED ITEMS
# ==========================================

print("\n" + "=" * 60)
print("DETECTED ITEMS")
print("=" * 60)


for i, flag in enumerate(
    red_flag_result["red_flags"],
    start=1
):

    print("\n")
    print(f"Item {i}")
    print("-" * 60)

    print(
        "Type:",
        flag["type"]
    )

    print(
        "Severity:",
        flag["severity"]
    )

    print(
        "Status:",
        flag["status"]
    )

    print(
        "AI Decision:",
        flag.get(
            "ai_decision",
            "Unknown"
        )
    )

    print(
        "AI Confidence:",
        flag.get(
            "ai_confidence",
            "Unknown"
        )
    )

    print(
        "Message:",
        flag["message"]
    )


    # ======================================
    # SOURCE EVIDENCE
    # ======================================

    if "evidence" in flag:

        print("\nEvidence:")
        print("-" * 40)

        print(
            flag["evidence"]
        )


    # ======================================
    # GEMINI AI ANALYSIS
    # ======================================

    if "ai_analysis" in flag:

        print("\nAI Analysis:")
        print("-" * 40)

        print(
            flag["ai_analysis"]
        )


# ==========================================
# POTENTIAL RED FLAGS
# ==========================================

print("\n" + "=" * 60)
print("POTENTIAL RED FLAGS")
print("=" * 60)


for i, flag in enumerate(
    red_flag_result[
        "potential_red_flag_items"
    ],
    start=1
):

    print(
        f"\n{i}. {flag['type']}"
    )

    print(
        "   Message:",
        flag["message"]
    )

    print(
        "   Confidence:",
        flag.get(
            "ai_confidence",
            "Unknown"
        )
    )


# ==========================================
# REVIEW / NORMAL CONTEXT
# ==========================================

print("\n" + "=" * 60)
print("REVIEW / NORMAL CONTEXT")
print("=" * 60)


for i, flag in enumerate(
    red_flag_result[
        "review_items_list"
    ],
    start=1
):

    print(
        f"\n{i}. {flag['type']}"
    )

    print(
        "   AI Decision:",
        flag.get(
            "ai_decision",
            "Unknown"
        )
    )


# ==========================================
# WORKFLOW COMPLETED
# ==========================================

print("\n" + "=" * 60)
print("WORKFLOW COMPLETED")
print("=" * 60)