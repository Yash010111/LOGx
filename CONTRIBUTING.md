# Contributing to LOGx

Thank you for your interest in contributing to LOGx! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Follow professional communication standards

## How to Contribute

### 1. Report Bugs

If you find a bug, please create an issue with:
- Clear title describing the problem
- Step-by-step reproduction instructions
- Expected vs. actual behavior
- Your system information (Python version, OS, etc.)
- Relevant error logs or screenshots

### 2. Suggest Features

Feature suggestions are welcome! Include:
- Clear description of the feature
- Use cases and benefits
- Possible implementation approach
- Any relevant examples or screenshots

### 3. Submit Code

#### Setup Development Environment

```bash
# Clone your fork
git clone https://github.com/yourusername/logx.git
cd logx

# Create feature branch
git checkout -b feature/my-feature

# Install dependencies with dev extras
uv sync --extra dev

# Make your changes
# ...
```

#### Code Style Requirements

We use automated formatting and linting:

```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Check code quality
uv run flake8 .

# Type checking
uv run mypy dashboard.py
```

**Before committing, ensure:**
- ✅ Code is formatted with Black
- ✅ No flake8 warnings
- ✅ Type hints are present
- ✅ Tests pass: `uv run pytest tests/ -v`

#### Commit Guidelines

```bash
# Good commit messages
git commit -m "feat: Add log filtering by severity level"
git commit -m "fix: Handle empty CSV gracefully"
git commit -m "docs: Update README with GPU instructions"
git commit -m "refactor: Extract log parsing to separate module"

# Commit types:
# feat:     A new feature
# fix:      A bug fix
# docs:     Documentation changes
# style:    Code style improvements (formatting)
# refactor: Code refactoring without behavior change
# test:     Adding or updating tests
# chore:    Build scripts, dependencies, etc.
```

#### Create Pull Request

1. Push to your fork:
   ```bash
   git push origin feature/my-feature
   ```

2. Open PR on GitHub with:
   - Clear description of changes
   - Reference related issues (#123)
   - Screenshots if UI changes
   - Test results

3. Wait for review and address feedback

#### PR Review Process

- Maintainers will review within 1-2 weeks
- Address all comments and suggestions
- Update PR with commit messages
- Request re-review when done

## Testing

All PRs must include tests:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_dashboard.py::test_single_log -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html

# Coverage should be >80%
```

### Writing Tests

Example test structure:

```python
import pytest
from dashboard import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_get(client):
    """Test GET request to index page"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Log Input' in response.data

def test_analysis_empty_input(client):
    """Test analysis with empty log input"""
    response = client.post('/', data={'log_input': ''})
    assert b'Please enter a log message' in response.data
```

## Documentation

Help improve docs:

1. Update [README.md](README.md) for user-facing changes
2. Add docstrings to new functions:
   ```python
   def analyze_log(log_text: str) -> dict:
       """
       Analyze a single log message.
       
       Args:
           log_text: Raw log message to analyze
           
       Returns:
           Dictionary with keys: log_type, explanation, 
           possible_root_causes, troubleshooting_steps
           
       Raises:
           ValueError: If log_text is empty
       """
   ```
3. Keep inline comments minimal - code should be self-documenting

## Project Structure

```
logx/
├── dashboard.py           # Main application
├── tests/                # Test suite
│   ├── test_dashboard.py
│   └── test_log_analysis.py
├── templates/            # HTML templates
├── static/              # CSS, JS
├── pyproject.toml       # UV configuration
├── README.md            # User guide
├── CONTRIBUTING.md      # This file
└── LICENSE              # MIT License
```

## Development Workflow

1. **Always work on a feature branch**
   ```bash
   git checkout -b feature/short-description
   ```

2. **Keep PRs focused**
   - One feature/bug per PR
   - Easier to review and merge

3. **Update related docs**
   - README if user-facing changes
   - Comments for code changes
   - Changelog entry

4. **Test locally before pushing**
   ```bash
   uv run black .
   uv run isort .
   uv run pytest tests/ -v
   uv run flake8 .
   ```

## Getting Help

- 💬 **Questions?** Open a Discussion
- 🐛 **Found a bug?** Create an Issue
- 💡 **Have an idea?** Start a Feature Request
- 📧 **Contact maintainers**: See README for contact info

## Recognition

Contributors will be:
- Listed in README
- Credited in release notes
- Given proper attribution

Thank you for contributing! 🎉
