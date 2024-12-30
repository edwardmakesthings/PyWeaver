# Contributing to PyWeaver

Thank you for your interest in contributing to PyWeaver! This guide will help you understand how to contribute effectively to the project.

## Development Setup

1. First, fork and clone the repository:
```bash
git clone https://github.com/yourusername/pyweaver.git
cd pyweaver
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Code Standards

PyWeaver follows these coding standards:

### Python Code Style
- We use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length is 88 characters
- Use type hints for all function arguments and return values
- Follow PEP 8 naming conventions:
  - snake_case for functions and variables
  - PascalCase for classes
  - UPPERCASE for constants

### Documentation Style
- All modules must have docstrings explaining their purpose
- All public functions and classes must have docstrings
- Follow Google-style docstring format:
```python
def example_function(arg1: str, arg2: int) -> bool:
    """Describe what the function does.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When and why this might be raised
    """
```

### Code Organization
- Keep modules focused and single-purpose
- Follow the established package structure
- Place tests in the tests directory mirroring the package structure

## Testing

We use pytest for testing. All code changes should include tests.

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file_combiner.py

# Run with coverage
pytest --cov=pyweaver
```

### Writing Tests
- Place tests in the `tests` directory
- Mirror the package structure in test files
- Use descriptive test names that explain the scenario being tested
- Include tests for both success and error cases
- Use fixtures for common setup code

Example test:
```python
def test_file_combining_removes_comments():
    """Test that comment removal works correctly."""
    content = textwrap.dedent('''
        # This is a comment
        def example():
            """This is a docstring."""
            # Another comment
            return True
    ''')

    result = process_content(content, ContentMode.NO_COMMENTS)
    assert "# This is a comment" not in result
    assert "This is a docstring" in result
```

## Pull Request Process

1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes, following our code standards

3. Add or update tests as needed

4. Run the test suite to ensure everything passes

5. Run the code formatter:
```bash
black pyweaver tests
```

6. Commit your changes:
```bash
git commit -m "Description of your changes"
```

7. Push to your fork:
```bash
git push origin feature/your-feature-name
```

8. Create a Pull Request on GitHub

### Pull Request Guidelines
- Use a clear, descriptive title
- Describe what changes you've made
- Mention any related issues
- Include notes on testing you've done
- List any breaking changes
- Add screenshots for UI changes

## Building Documentation

To build and view the documentation locally:

1. Install documentation dependencies:
```bash
pip install -e ".[docs]"
```

2. Serve the documentation:
```bash
mkdocs serve
```

3. View at http://127.0.0.1:8000

### Documentation Guidelines
- Keep language clear and concise
- Include code examples for features
- Update relevant documentation with code changes
- Test documentation examples to ensure they work
- Add docstrings for all public API elements

## Getting Help

- Open an issue for bugs or feature requests
- Ask questions in discussions
- Join our community chat
- Review existing issues and PRs for similar topics

## Code of Conduct

Please note that PyWeaver has a Code of Conduct. By participating in this project, you agree to abide by its terms. We expect all contributors to:

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## License

By contributing to PyWeaver, you agree that your contributions will be licensed under the same license as the project (MIT License).