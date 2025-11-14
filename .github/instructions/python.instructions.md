---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
---

# Python Coding Conventions

## Python Instructions

- Ensure functions have descriptive names and always use type hints.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.
- Whenever code is added or modified, ensure that all tests pass and that the code adheres to the specified style guidelines using `ruff`.

## Tooling

- Use `uv` (https://uv.run/) for managing virtual environments and dependencies.
  - This means you will always have to use `uv run` to execute scripts, tests and commands.
- Use the (src layout)[https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/] for project structure.
- Use `pytest` for testing.
- Use `ruff` for code formatting, import sorting, and linting.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where
  appropriate.
- Put imports at the top of the file, not in functions, arranged by isort.
- Follow the recommendations for these sections from the Google style guide:
  - [2.2.4 Imports](https://google.github.io/styleguide/pyguide.html#224-decision)
  - [3.4.1 Trailing commas in sequences of items](https://google.github.io/styleguide/pyguide.html#341-trailing-commas-in-sequences-of-items)

### Comments and Docstrings

- Write clear and concise comments for each function.
- Provide docstrings following PEP 257 conventions.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Follow the recommendations for these sections from the Google style guide:
  - [3.8 Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

## Edge Cases and Testing

- Handle edge cases and write clear exception handling.
- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

## Example of Proper Documentation

```python
def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle given the radius.

    Parameters:
    radius (float): The radius of the circle.

    Returns:
    float: The area of the circle, calculated as π * radius^2.
    """
    import math
    return math.pi * radius ** 2
```
