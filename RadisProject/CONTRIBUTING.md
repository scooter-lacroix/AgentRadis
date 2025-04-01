# Contributing to RadisProject

Thank you for your interest in contributing to RadisProject! This document provides guidelines and instructions to help you get started as a contributor.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Development Environment Setup](#development-environment-setup)
- [Coding Standards](#coding-standards)
- [Branch Naming and Git Workflow](#branch-naming-and-git-workflow)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Communication](#communication)

## Code of Conduct

We expect all contributors to follow our Code of Conduct. Please be respectful and considerate in all interactions with the community.

## Development Environment Setup

### Prerequisites
- Python 3.9 or higher
- Git
- Conda or pip for package management

### Setting Up Your Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/RadisProject.git
   cd RadisProject
   ```

2. **Create a virtual environment**
   
   Using Conda:
   ```bash
   conda create -n radis-env python=3.11
   conda activate radis-env
   ```
   
   Using venv:
   ```bash
   python -m venv radis-env
   # On Windows
   radis-env\Scripts\activate
   # On Unix or MacOS
   source radis-env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **GPU Setup (Optional)**
   
   For CUDA:
   ```bash
   pip install torch==2.1.0+cu118 -f https://download.pytorch.org/whl/cu118/torch_stable.html
   ```
   
   For ROCm:
   ```bash
   pip install torch==2.1.0+rocm5.6 -f https://download.pytorch.org/whl/rocm5.6/torch_stable.html
   ```

5. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Coding Standards

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) standards for Python code. Here are some key points:

### Python Style Guidelines

- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters (using Black formatter)
- Use meaningful variable and function names
- Write docstrings for all functions, classes, and modules using the Google style:
  ```python
  def function_with_types_in_docstring(param1, param2):
      """Example function with types documented in the docstring.
      
      Args:
          param1 (int): The first parameter.
          param2 (str): The second parameter.
          
      Returns:
          bool: The return value. True for success, False otherwise.
      """
      return True
  ```

### Code Quality Tools

We use the following tools to maintain code quality:

- **Black**: For automatic code formatting
  ```bash
  black app/ tests/
  ```

- **isort**: For sorting imports
  ```bash
  isort app/ tests/
  ```

- **Flake8**: For linting
  ```bash
  flake8 app/ tests/
  ```

- **mypy**: For static type checking
  ```bash
  mypy app/
  ```

## Branch Naming and Git Workflow

### Branch Naming Convention

Use the following format for branch names:
```
<type>/<issue-number>-<short-description>
```

Where `<type>` is one of:
- `feature`: New feature implementation
- `bugfix`: Bug fixes
- `hotfix`: Critical bug fixes to production
- `docs`: Documentation changes
- `test`: Adding or modifying tests
- `refactor`: Code refactoring
- `perf`: Performance improvements

Examples:
```
feature/123-add-new-tool
bugfix/234-fix-memory-leak
docs/345-update-readme
```

### Git Workflow

1. Create a new branch from `main` for your work
2. Make your changes in small, focused commits
3. Write meaningful commit messages
4. Push your branch to your fork
5. Create a pull request

## Pull Request Process

1. **Before submitting a PR:**
   - Ensure all tests pass locally
   - Run linting and formatting checks
   - Update documentation if necessary
   - Add tests for new functionality

2. **PR Description Template:**
   ```markdown
   ## Description
   Brief description of the changes

   ## Related Issue
   Fixes #(issue)

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update

   ## Testing
   Describe the tests that you ran

   ## Checklist
   - [ ] My code follows the style guidelines
   - [ ] I have performed a self-review
   - [ ] I have commented my code, particularly in hard-to-understand areas
   - [ ] I have made corresponding documentation changes
   - [ ] My changes generate no new warnings
   - [ ] I have added tests that prove my fix is effective or that my feature works
   - [ ] New and existing unit tests pass locally with my changes
   ```

3. **Review Process:**
   - At least one core maintainer must approve your PR
   - Address all review comments
   - Once approved, a maintainer will merge your PR

## Testing Requirements

### Test Coverage

All new code should be covered by tests. We aim for at least 85% code coverage.

### Types of Tests

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test how components work together
- **Functional Tests**: Test complete features from a user perspective

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_file.py

# Run tests with specific markers
pytest -m "not slow"
```

### Writing Tests

- Test files should be placed in the `tests/` directory
- Test file names should follow the pattern `test_*.py`
- Test functions should be named `test_*`
- Use meaningful test names that describe what is being tested
- Use fixtures for common setup and teardown

Example:
```python
import pytest
from app.tool import SomeTool

def test_some_tool_returns_expected_result():
    tool = SomeTool()
    result = tool.process("input")
    assert result == "expected output"
```

## Documentation Standards

### General Guidelines

- Write clear, concise documentation
- Use proper English grammar and spelling
- Update documentation when you change code
- Use Markdown for formatting

### Documentation Types

1. **Code Documentation**:
   - Document all public methods, functions, and classes
   - Include type hints and docstrings
   - Explain complex logic with inline comments

2. **User Documentation**:
   - Update user guides when adding features
   - Include examples for new functionality
   - Ensure documentation is accessible to new users

3. **Architecture Documentation**:
   - Document design decisions
   - Keep diagrams up-to-date

### README and High-Level Docs

When updating core functionality, ensure the README.md and high-level documentation in the `docs/` directory are updated to reflect your changes.

## Communication

- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and general discussion
- **Pull Requests**: Use pull requests for code reviews and discussions about implementation

---

Thank you for contributing to RadisProject! Your efforts help make this project better for everyone.

