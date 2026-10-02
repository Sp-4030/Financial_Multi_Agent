from workflow.graph import financial_workflow



# PDF Path
pdf_path = r"C:\Users\Shantanu\Desktop\Reports\Epam.pdf"



# Initial State
initial_state = {
    "pdf_path": pdf_path
}



# Run Workflow
result = financial_workflow.invoke(
    initial_state
)



# Display Results
print("\n" + "=" * 60)
print("MULTI-AGENT WORKFLOW RESULT")


print("\nDocument Result:")
print(result["document_result"])


print("\nFinancial Metrics:")
print(result["extracted_metrics"])


print("\nRed Flag Result:")
print(result["red_flag_result"])


print("\n" + "=" * 60)
print("WORKFLOW COMPLETED")
