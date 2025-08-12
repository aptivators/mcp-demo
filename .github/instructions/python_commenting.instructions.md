---
applyTo: "**/*.py"
---
You are an expert in Python documentation and code commenting. Follow these guidelines to write clear, consistent, and maintainable documentation.

# Module-Level Documentation

Every Python module should begin with a docstring that includes:
- Module purpose and functionality
- Key features and capabilities
- Usage examples
- Dependencies and requirements
- Author and version information

Example:
```python
"""
PII (Personally Identifiable Information) Handler Server

This server provides functionality to detect, mask, and restore PII in text.
It uses SQLite for storing PII mappings and provides an MCP interface for integration
with Claude.ai desktop.

Features:
- Detects common PII types (names, addresses, contact info, etc.)
- Masks PII with standardized placeholders
- Restores original PII values
- Maintains text structure and formatting
- Complete PII processing flow with sanitization and restoration
"""
```

# Function Documentation

Use Google-style docstrings for all functions:
```python
def function_name(param1: type, param2: type) -> return_type:
    """Function description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: Description of when this exception is raised
        
    Examples:
        >>> function_name(1, 2)
        3
    """
```

# Class Documentation

Document classes with comprehensive docstrings:
```python
class MyClass:
    """Class description.
    
    This class handles...
    
    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
        
    Examples:
        >>> instance = MyClass()
        >>> instance.method()
    """
```

# Type Hints and Annotations

Always include type hints:
```python
from typing import List, Dict, Optional

def process_data(
    items: List[str],
    config: Optional[Dict[str, str]] = None
) -> Dict[str, List[str]]:
    """Process a list of items with optional configuration."""
```

# Inline Comments

Add comments for:
- Complex logic blocks
- Non-obvious code decisions
- Workarounds or temporary solutions
- TODO items
- External documentation references

Example:
```python
# TODO: Implement caching for better performance
# Reference: https://docs.python.org/3/library/functools.html#functools.lru_cache
@lru_cache(maxsize=128)
def expensive_operation():
    # This is a workaround for the known issue with concurrent access
    # See: https://github.com/python/cpython/issues/12345
    pass
```

# Error Handling Documentation

Document exceptions and error handling:
```python
def process_file(filename: str) -> str:
    """Process a file and return its contents.
    
    Args:
        filename: Path to the file to process
        
    Returns:
        Processed file contents
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file cannot be accessed
        ValueError: If the file format is invalid
    """
```

# Security Documentation

Document security considerations:
```python
def handle_sensitive_data(data: str) -> str:
    """Process sensitive data with security measures.
    
    Security Notes:
    - Input is sanitized to prevent XSS attacks
    - Data is encrypted before storage
    - Access is logged for audit purposes
    - PII is masked in logs
    """
```

# Performance Documentation

Document performance characteristics:
```python
def process_large_dataset(items: List[str]) -> List[str]:
    """Process a large dataset efficiently.
    
    Performance Notes:
    - Time Complexity: O(n log n)
    - Space Complexity: O(n)
    - Uses memory mapping for large files
    - Implements batch processing for efficiency
    """
```

# Testing Documentation

Document test requirements:
```python
def calculate_total(items: List[float]) -> float:
    """Calculate the total of a list of numbers.
    
    Test Cases:
    - Empty list returns 0
    - List with negative numbers
    - List with floating point numbers
    - List with very large numbers
    """
```

# API Documentation

Document API endpoints:
```python
@mcp.tool()
async def process_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process an API request.
    
    API Endpoint: /api/v1/process
    
    Request Format:
    {
        "input": str,
        "options": Dict[str, Any]
    }
    
    Response Format:
    {
        "result": Any,
        "status": str,
        "message": str
    }
    """
```

# Configuration Documentation

Document configuration options:
```python
def initialize_app(config: Dict[str, Any]) -> None:
    """Initialize the application with configuration.
    
    Configuration Options:
    - debug: bool - Enable debug mode
    - log_level: str - Logging level (DEBUG, INFO, WARNING, ERROR)
    - max_workers: int - Maximum number of worker threads
    - timeout: int - Request timeout in seconds
    """
```

# Maintenance Documentation

Document maintenance procedures:
```python
def perform_maintenance() -> None:
    """Perform system maintenance tasks.
    
    Maintenance Tasks:
    1. Clean up temporary files
    2. Rotate log files
    3. Update database indices
    4. Clear cache
    
    Frequency: Daily at 2 AM UTC
    """
```

# Version Control Documentation

Document version history:
```python
def new_feature() -> None:
    """Implement new feature.
    
    Version History:
    - v1.0.0: Initial implementation
    - v1.1.0: Added caching support
    - v1.2.0: Improved error handling
    
    Breaking Changes:
    - v1.1.0: Changed return type of process_data()
    - v1.2.0: Removed deprecated methods
    """
```

# Documentation Best Practices

1. Be Consistent
   - Use consistent formatting
   - Follow standard documentation style
   - Use consistent terminology
   - Maintain consistent level of detail
   - Use consistent examples

2. Be Clear
   - Write clear and concise documentation
   - Use simple and direct language
   - Avoid technical jargon when possible
   - Provide clear examples
   - Use diagrams when helpful

3. Be Complete
   - Cover all important aspects
   - Include all necessary details
   - Provide comprehensive examples
   - Document all edge cases
   - Include all required information

4. Be Maintainable
   - Keep documentation up to date
   - Review and update regularly
   - Remove outdated information
   - Add new information as needed
   - Maintain version history

5. Be Accessible
   - Make documentation easy to find
   - Organize logically
   - Use clear headings
   - Include table of contents
   - Provide search functionality


