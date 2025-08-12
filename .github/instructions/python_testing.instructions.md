---
applyTo: "**/*.py"
---
# Python Testing Standards

## Test-Driven Development (TDD)

### Core Principles
- Follow the Red-Green-Refactor cycle:
  1. Write failing test (Red)
  2. Write minimal code to pass test (Green)
  3. Refactor while keeping tests passing (Refactor)
- Write tests before implementing features
- Keep test cycles short and focused
- Use meaningful test names that describe behavior
- One assertion per test when possible

### TDD Workflow
- Start with the simplest test case
- Write tests for edge cases and error conditions
- Implement minimal code to pass tests
- Refactor without changing behavior
- Repeat until feature is complete

## Unit Testing

### Test Structure
- Use `pytest` as the testing framework
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests independent and isolated
- Use fixtures for common setup and teardown
- Group related tests in classes or modules

### Test Organization
- Mirror the structure of the code being tested
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Group tests by functionality
- Use test classes for related test cases
- Keep test files focused and single-purpose

### Test Fixtures
- Use `@pytest.fixture` for reusable test components
- Scope fixtures appropriately (function, class, module, session)
- Use fixture factories for dynamic test data
- Clean up resources in fixture teardown
- Share fixtures across test modules when appropriate

### Mocking and Stubbing
- Use `unittest.mock` or `pytest-mock` for mocking
- Mock external dependencies
- Use `patch` decorator for class and module mocking
- Verify mock interactions when necessary
- Use `MagicMock` for complex mock objects
- Avoid mocking what you don't own

### Test Data
- Use factories for test data generation
- Keep test data minimal and focused
- Use constants for test values
- Avoid hardcoding test data
- Use parameterized tests for multiple scenarios

## Integration Testing

### API Testing
- Use `pytest` with `requests` or `httpx` for API testing
- Test all HTTP methods (GET, POST, PUT, DELETE)
- Verify response status codes
- Validate response payload structure
- Test error handling and edge cases
- Use environment variables for API endpoints

### Database Testing
- Use test database for integration tests
- Clean up test data after each test
- Use transactions for test isolation
- Test database migrations
- Verify data integrity
- Use database fixtures for common operations

### External Service Testing
- Mock external service calls in unit tests
- Use integration tests for real service interaction
- Test service failure scenarios
- Verify retry mechanisms
- Test rate limiting and timeouts

## Test Automation

### CI/CD Integration
- Run tests automatically on every commit
- Use GitHub Actions or similar CI tools
- Configure test environments in CI
- Run tests in parallel when possible
- Generate and publish test reports
- Enforce minimum test coverage

### Test Coverage
- Aim for high test coverage (80%+)
- Use `pytest-cov` for coverage reporting
- Focus on critical path coverage
- Don't sacrifice quality for coverage
- Review coverage reports regularly
- Exclude generated code from coverage

### Performance Testing
- Use `pytest-benchmark` for performance tests
- Test response times and throughput
- Monitor memory usage
- Test under load conditions
- Profile slow tests
- Use appropriate timeouts

## Best Practices

### Test Quality
- Keep tests simple and readable
- Avoid test code duplication
- Use helper functions for common operations
- Document complex test scenarios
- Review test code regularly
- Refactor tests when necessary

### Error Handling
- Test both success and failure cases
- Verify error messages and codes
- Test exception handling
- Validate error responses
- Test edge cases and boundaries
- Use appropriate assertions

### Security Testing
- Test authentication and authorization
- Verify input validation
- Test security headers
- Check for common vulnerabilities
- Test rate limiting
- Verify secure communication

### Test Maintenance
- Keep tests up to date with code changes
- Remove obsolete tests
- Update test data when needed
- Monitor test execution time
- Address flaky tests promptly
- Document test requirements

## Tools and Configuration

### Required Tools
- pytest
- pytest-cov
- pytest-mock
- pytest-benchmark
- requests/httpx
- factory-boy (for test data)

### Configuration
- Use `pytest.ini` for test configuration
- Configure test markers
- Set up test environments
- Define test categories
- Configure test reporting
- Set up test databases

### Test Environment
- Use separate test environment
- Configure test dependencies
- Set up test databases
- Configure test services
- Use environment variables
- Document setup requirements

## Documentation

### Test Documentation
- Document test requirements
- Explain test scenarios
- Document test data
- Describe test environment
- Document test procedures
- Keep documentation up to date

### Test Reports
- Generate test reports
- Include coverage information
- Document test results
- Track test metrics
- Share test insights
- Use test analytics

## Common Patterns

### Test Patterns
- Use test factories
- Implement test builders
- Use test doubles
- Apply test data builders
- Use test helpers
- Implement test utilities

### Anti-patterns to Avoid
- Don't test implementation details
- Avoid test interdependence
- Don't ignore failing tests
- Avoid test code duplication
- Don't make tests too complex
- Avoid testing private methods

