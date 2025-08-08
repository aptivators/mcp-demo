# Medicare MCP Server

This directory contains the Medicare MCP server and related modules for serving, analyzing, and answering questions about Medicare datasets and documents.

## Structure

- `medicare_server.py`: Main entry point for the Medicare MCP server, exposing resources, tools, and prompts.
- `datasets.py`: Utilities for fetching datasets, reading documents, and listing available files.
- `decorators.py`: Decorators for access control and other shared logic.

## medicare_server.py Capabilities

### Resources

- Exposes Medicare datasets as resources (e.g., nursing home, deficit reduction datasets)
- Exposes Medicare documents as resources for direct access

### Tools

- Row count for datasets
- List available datasets and documents
- List dataset columns
- Summarize numeric columns (min, max, average)
- Search and answer questions from Medicare documents
- Read document contents

### Prompts

- Explain available datasets, documents, and tools
- Guide agents on combining tools and resources (`explain_tool_resource_flow`)
- Explain role escalation policy for authorization (`explain_role_escalation_policy`)
- Notify user when processing a request (`notify_user_processing`)
- Provide dataset and document access instructions

## datasets.py Capabilities

- Fetches datasets by ID
- Reads and lists available documents
- Provides dataset metadata

## decorators.py Capabilities

- Provides access control decorators (e.g., `require_admin` for admin-only resources)

## Usage

From the project root, run:

```sh
uv run mcp dev servers/medicare_server.py
```

Or, if you need to set the Python path:

```sh
PYTHONPATH=. uv run mcp dev servers/medicare_server.py
```

## Adding Datasets or Documents

- To add a new dataset, update `datasets.py` with the new dataset ID.
- To add a new document, place the file in `documents/medicare/`.

## Agent Guidance

- Use the `explain_tool_resource_flow` prompt for an overview of how to combine tools and resources.
- Use `list_medicare_datasets` and `list_medicare_documents` to discover available data.
- Refer to the prompts in `medicare_server.py` for guidance on role escalation, user notifications, and more.

---
For more details, see the code comments and prompts in `medicare_server.py`.
