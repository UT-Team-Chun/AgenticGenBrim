# /impl

Select the appropriate sub-agent for the given task and implement in the following order.
If the review in step 2 finds issues, return to step 1 to fix them. Repeat steps 1 and 2 until all reviews pass.

Arguments: $ARGUMENTS

1. Implement the feature according to the task requirements

- Select the appropriate agent based on the task content
  - Designer/RAG related: `designer-impl` agent
  - IFC conversion related: `ifc-impl` agent
- Thoroughly understand the project before implementing based on requirements
- Apply formatting with `make fmt`
- Verify there are no Lint errors with `make lint`

2. Verify the implementation meets the requirements

- Always use the `quality-check` agent for verification
- Thoroughly review for missing requirements, bugs, security risks, and other potential issues

## Tech Stack

- Python 3.13 / uv
- OpenAI API (Responses API / Structured Output)
- Pydantic / StrEnum
- ifcopenshell (IFC output)
- text-embedding-3-small (embeddings)
- pdfplumber / pypdf / pymupdf4llm (PDF extraction)
- fire (CLI)
- Ruff (Lint/Format)
