---
applyTo: "**/*.py"
---
# Python Formatting Standards

## Code Style and Formatting

### General Principles
- Follow PEP 8 style guide for Python code
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters (Black formatter default)
- Use UTF-8 encoding for all files
- Use Unix-style line endings (LF)

### Naming Conventions
- Use `snake_case` for:
  - Variables
  - Functions
  - Methods
  - Modules
  - Packages
- Use `PascalCase` for:
  - Classes
  - Type aliases
- Use `UPPER_CASE` for:
  - Constants
  - Module-level variables that should not be modified
- Use descriptive names that reflect purpose
- Avoid single-letter names except for loop variables (i, j, k)
- Prefix private attributes with single underscore (_)

### Imports
- Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- Sort imports alphabetically within each group
- Use absolute imports over relative imports
- Use `from x import y` for specific imports
- Use `import x` for module imports
- One import per line

### Whitespace
- Two blank lines before top-level functions and classes
- One blank line before class methods
- One blank line between logical sections within functions
- No blank lines between related one-liners
- No spaces around parentheses in function calls
- No spaces around brackets in list/dict access
- One space after commas
- One space around operators
- No spaces around default parameter values

### Comments and Documentation
- Use docstrings for all public modules, functions, classes, and methods
- Follow Google-style docstring format with the following sections:
  - Args: Document all parameters with types and descriptions
  - Returns: Document return value type and description
  - Raises: Document all exceptions that may be raised
  - Examples: Include usage examples when helpful
- Use inline comments sparingly and only when necessary
- Comments should be complete sentences
- Start comments with a space
- Keep comments up-to-date with code changes
- Keep documentation close to code

### Type Hints
- Use type hints for all function parameters and return values
- Use `typing` module for complex types
- Use `Optional[Type]` for parameters that can be None
- Use `Union[Type1, Type2]` for parameters that can be multiple types
- Use `Any` sparingly and only when necessary
- When using Optional parameters, provide type hints like:
  ```python
  def function(param: Optional[str] = None) -> str:
  ```

### Function and Method Definitions
- Prefer 3 or fewer parameters per function
- For functions requiring more parameters, use dataclasses or parameter objects
- Use keyword arguments for clarity
- Default parameter values should be immutable
- Return early to avoid deep nesting
- Keep functions focused and single-purpose
- Maximum function length of 50 lines

### Classes
- Keep classes focused and single-responsibility
- Use composition over inheritance
- Document all public methods and properties
- Use `@property` decorator for computed attributes
- Use `@dataclass` for simple data containers
- Maximum class length of 200 lines

### Error Handling
- Use specific exception types
- Catch exceptions as close to their source as possible
- Use context managers (`with` statements) for resource management
- Log exceptions with appropriate context
- Use custom exceptions for domain-specific errors
- Write tests for both success and error cases
- Test custom exceptions explicitly

### Testing
- Use `pytest` for testing
- Follow AAA pattern (Arrange, Act, Assert)
- Use descriptive test names
- One assertion per test when possible
- Use fixtures for test setup and teardown
- Mock external dependencies
- Write tests for both success and error cases
- Test custom exceptions explicitly

### Code Organization
- One class per file
- Related functions should be grouped together
- Use `__init__.py` files to define package interfaces
- Keep circular dependencies to a minimum
- Use `if __name__ == "__main__":` for script entry points

### Performance
- Use list comprehensions over for loops when appropriate
- Use generator expressions for large datasets
- Use `collections` module for specialized containers
- Profile code before optimizing
- Use appropriate data structures for the task
- Never sacrifice security for performance
- Use appropriate security measures even if they impact performance

### Security
- Never store sensitive data in code
- Use environment variables for configuration
- Validate all user input
- Use parameterized queries for database operations
- Follow principle of least privilege
- Never sacrifice security for performance
- Use appropriate security measures even if they impact performance

### Tools
- Use `black` for code formatting
- Use `isort` for import sorting
- Use `flake8` for linting
- Use `mypy` for type checking
- Use `pylint` for additional code analysis
- Use `pre-commit` hooks to enforce standards

### Version Control
- Write clear, descriptive commit messages
- Keep commits focused and atomic
- Use feature branches for development
- Review code before merging
- Keep merge conflicts to a minimum

### Documentation
- Keep README.md up to date
- Document all public APIs
- Include examples in docstrings
- Document configuration options
- Keep documentation close to code


