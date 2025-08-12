---
applyTo: "**/*.py"
---

  You are an expert in Python, FastAPI, and scalable API development.
  
  Key Principles
  - Write concise, technical responses with accurate Python examples.
  - Use functional, declarative programming; avoid classes where possible.
  - Prefer iteration and modularization over code duplication.
  - Use descriptive variable names with auxiliary verbs (e.g., is_active, has_permission).
  - Use lowercase with underscores for directories and files (e.g., routers/user_routes.py).
  - Favor named exports for routes and utility functions.
  - Use the Receive an Object, Return an Object (RORO) pattern.
  
  Python/FastAPI
  - Use def for pure functions and async def for asynchronous operations.
  - Use type hints for all function signatures. Prefer Pydantic models over raw dictionaries for input validation.
  - File structure: exported router, sub-routes, utilities, static content, types (models, schemas).
  - Avoid unnecessary curly braces in conditional statements.
  - For single-line statements in conditionals, omit curly braces.
  - Use concise, one-line syntax for simple conditional statements (e.g., if condition: do_something()).
  
  Error Handling and Validation
  - Prioritize error handling and edge cases:
    - Handle errors and edge cases at the beginning of functions.
    - Use early returns for error conditions to avoid deeply nested if statements.
    - Place the happy path last in the function for improved readability.
    - Avoid unnecessary else statements; use the if-return pattern instead.
    - Use guard clauses to handle preconditions and invalid states early.
    - Implement proper error logging and user-friendly error messages.
    - Use custom error types or error factories for consistent error handling.
  
  Dependencies
  - FastAPI
  - Pydantic v2
  - Async database libraries like asyncpg or aiomysql
  - SQLAlchemy 2.0 (if using ORM features)
  
  FastAPI-Specific Guidelines
  - Use functional components (plain functions) and Pydantic models for input validation and response schemas.
  - Use declarative route definitions with clear return type annotations.
  - Use def for synchronous operations and async def for asynchronous ones.
  - Minimize @app.on_event("startup") and @app.on_event("shutdown"); prefer lifespan context managers for managing startup and shutdown events.
  - Use middleware for logging, error monitoring, and performance optimization.
  - Optimize for performance using async functions for I/O-bound tasks, caching strategies, and lazy loading.
  - Use HTTPException for expected errors and model them as specific HTTP responses.
  - Use middleware for handling unexpected errors, logging, and error monitoring.
  - Use Pydantic's BaseModel for consistent input/output validation and response schemas.
  
  Performance Optimization
  - Minimize blocking I/O operations; use asynchronous operations for all database calls and external API requests.
  - Implement caching for static and frequently accessed data using tools like Redis or in-memory stores.
  - Optimize data serialization and deserialization with Pydantic.
  - Use lazy loading techniques for large datasets and substantial API responses.
  
  Key Conventions
  1. Rely on FastAPI's dependency injection system for managing state and shared resources.
  2. Prioritize API performance metrics (response time, latency, throughput).
  3. Limit blocking operations in routes:
     - Favor asynchronous and non-blocking flows.
     - Use dedicated async functions for database and external API operations.
     - Structure routes and dependencies clearly to optimize readability and maintainability.
  
  Refer to FastAPI documentation for Data Models, Path Operations, and Middleware for best practices.

# Python Project Best Practices (Updated)

## Package Structure
- Every directory intended as a Python package **must** contain an empty `__init__.py` file.
- Use relative imports (e.g., `from .module import ...`) for internal modules within a package.
- For parent-level imports, use double-dot notation (e.g., `from ..subpackage.module import ...`).
- Always run your FastAPI or Python app from the project root using the full module path (e.g., `uvicorn backend.main:app --reload`).

## Environment and Dependency Management with uv
- Use [`uv`](mdc:https:/github.com/astral-sh/uv) for fast, modern Python dependency management and virtual environments.
- To create a new virtual environment:
  ```bash
  uv venv
  ```
- To activate the environment (Windows):
  ```bash
  .venv\Scripts\activate
  ```
- To install dependencies:
  ```bash
  uv pip install -r requirements.txt
  ```
- To add a new dependency:
  ```bash
  uv pip install <package>
  ```
- To run your FastAPI app:
  ```bash
  uvicorn backend.main:app --reload
  ```

## Summary Table
| Task                        | Command/Practice                                 |
|-----------------------------|--------------------------------------------------|
| Create venv                 | `uv venv`                                        |
| Activate venv (Windows)     | `.venv\Scripts\activate`                         |
| Install dependencies        | `uv pip install -r requirements.txt`             |
| Add dependency              | `uv pip install <package>`                       |
| Run FastAPI app             | `uvicorn backend.main:app --reload`              |
| Ensure package recognition  | Add `__init__.py` to all package directories     |
| Use internal imports        | Use relative imports (e.g., `from .module import ...`) |

## Notes
- Never commit secrets or credentials to version control.
- Always use `__init__.py` files for package recognition.
- Use relative imports for maintainable, portable code.
- Use `uv` for fast, reproducible Python environments.

  