# Medicare MCP Project

This project provides a Model Context Protocol (MCP) server for exploring, analyzing, and answering questions about Medicare datasets and documents.

## Structure

- `servers/` — Contains the main MCP server, dataset/document utilities, and access control decorators.
- `documents/medicare/` — Sample Medicare-related documents for use by the server and agent.
- `pyproject.toml`, `uv.lock` — Project dependencies and environment configuration.

## Running the Server

From the project root, run:

```sh
uv run mcp dev servers/medicare_server.py
```

If you encounter import errors, set the Python path:

```sh
PYTHONPATH=. uv run mcp dev servers/medicare_server.py
```

## Client Interface (Placeholder)

A client interface for interacting with the MCP server will be added here. This may include a web UI, CLI, or integration instructions for agents and end users.

## Adding Data

- To add a new dataset, update `servers/datasets.py` with the new dataset ID.
- To add a new document, place the file in `documents/medicare/`.

## Agent Guidance

- Use the prompts in `servers/medicare_server.py` for workflow and tool/resource usage instructions.
- See the `servers/README.md` for more details on server-side features.

---
For more information, see the code and documentation in the `servers` directory.

## Testing

The `server-test.ps1` file can be executed from the PowerShell commandline. The recommended usage for readability is:

```sh
cd .\tests
.\server-test.ps1
```

or to log the console output to file:

```sh
cd .\tests
.\server-test.ps1 *> ..\logs\server-test.log
```
