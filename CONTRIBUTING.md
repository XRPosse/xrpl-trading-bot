# Contributing to XRPL Trading Bot

Thank you for your interest in contributing to the XRPL Trading Bot! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity.

### Expected Behavior

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/xrpl-trading-bot.git
   cd xrpl-trading-bot
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/originalowner/xrpl-trading-bot.git
   ```
4. **Create a virtual environment** and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

## How to Contribute

### Reporting Bugs

- Use the GitHub Issues tracker
- Check if the issue already exists
- Include:
  - Clear bug description
  - Steps to reproduce
  - Expected vs actual behavior
  - System information (OS, Python version)
  - Relevant logs or error messages

### Suggesting Features

- Open a GitHub Issue with [Feature Request] tag
- Explain the problem your feature solves
- Provide use cases
- Consider implementation complexity

### Contributing Code

1. **Find an issue** to work on or create one
2. **Comment** on the issue to claim it
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes**
5. **Test thoroughly**
6. **Submit a pull request**

## Development Process

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

Examples:
- `feature/add-rsi-indicator`
- `fix/websocket-reconnection`
- `docs/update-installation-guide`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```bash
git commit -m "feat(strategy): add RSI indicator to momentum strategy"
git commit -m "fix(backtest): correct commission calculation"
git commit -m "docs(readme): update installation instructions"
```

## Style Guidelines

### Python Code Style

We use [PEP 8](https://pep8.org/) with the following tools:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Before committing:
```bash
black .
isort .
flake8 .
mypy src/
```

### Code Principles

1. **Type Hints**: Use type hints for function parameters and returns
   ```python
   def calculate_position_size(
       balance: Decimal,
       risk_percent: float
   ) -> Decimal:
       ...
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def analyze_market(data: pd.DataFrame) -> Dict[str, Any]:
       """Analyze market data for trading signals.
       
       Args:
           data: DataFrame with OHLCV data
           
       Returns:
           Dictionary containing signal and metadata
       """
   ```

3. **Error Handling**: Use specific exceptions and log errors
   ```python
   try:
       result = risky_operation()
   except SpecificError as e:
       logger.error(f"Operation failed: {e}")
       raise
   ```

4. **Async Best Practices**: Use async/await properly
   ```python
   async def fetch_data() -> pd.DataFrame:
       async with aiohttp.ClientSession() as session:
           ...
   ```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_strategies.py

# Run in verbose mode
pytest -v
```

### Writing Tests

1. **Test File Naming**: `test_<module_name>.py`
2. **Test Function Naming**: `test_<description>`
3. **Use Fixtures**: For common test data
4. **Test Edge Cases**: Empty data, extreme values, errors

Example:
```python
@pytest.mark.asyncio
async def test_strategy_buy_signal(momentum_strategy, bullish_market_data):
    signal = await momentum_strategy.analyze(bullish_market_data)
    assert signal["action"] == "buy"
    assert signal["confidence"] > 0.6
```

### Test Coverage

- Aim for >80% code coverage
- Test all public methods
- Include integration tests
- Add performance tests for critical paths

## Documentation

### Code Documentation

- All public functions need docstrings
- Complex algorithms need inline comments
- Update existing docs when changing functionality

### User Documentation

- Update relevant `.md` files in `docs/`
- Include code examples
- Add screenshots for UI changes
- Keep language clear and concise

### API Documentation

- Document all public APIs
- Include parameter types and descriptions
- Provide usage examples
- Note any breaking changes

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Rebase your feature branch**:
   ```bash
   git checkout feature/your-feature
   git rebase main
   ```

3. **Run all checks**:
   ```bash
   black . && isort . && flake8 . && pytest
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

5. **Create Pull Request**:
   - Use descriptive title
   - Reference related issues
   - Describe changes made
   - Include test results
   - Add screenshots if applicable

### PR Review Process

- All PRs require at least one review
- Address reviewer feedback
- Keep PR scope focused
- Update branch with main if needed
- Squash commits if requested

### After Merge

- Delete your feature branch
- Update your local main
- Celebrate your contribution! 🎉

## Questions?

- Check existing [Issues](https://github.com/yourusername/xrpl-trading-bot/issues)
- Join [Discussions](https://github.com/yourusername/xrpl-trading-bot/discussions)
- Read the [Documentation](docs/)

Thank you for contributing to XRPL Trading Bot!