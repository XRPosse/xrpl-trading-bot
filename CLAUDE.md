# Claude Project Configuration - Python

## Quick Start - Run This First!
```bash
# Auto-setup virtual environment and activate it
if [ ! -d "venv" ]; then python -m venv venv; fi && source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
# Install dependencies if they exist
[ -f "requirements.txt" ] && pip install -r requirements.txt
# Show current environment
echo "Using Python at: $(which python)"
```

## Project Overview
**Type**: Python Project  
**Initialized**: 2025-07-14  
**Python Version**: [VERSION]  
**Framework**: [Django/Flask/FastAPI/None]  
**Purpose**: [Brief project description]

## Key Directories
- `/docs` - Comprehensive project documentation
- `/src` or `/app` - Main application code
- `/tests` - Test suites (unit, integration)
- `/scripts` - Utility and automation scripts
- `/config` - Configuration files
- `/data` - Data files (if applicable)
- `/notebooks` - Jupyter notebooks (if applicable)
- `/.github` - GitHub workflows and actions

## Development Workflow

### 1. Before Starting Work
```bash
# Check Python version
python --version
pip --version

# Check for virtual environment and create if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate  # Linux/Mac
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows Git Bash
else
    echo "Error: Could not find virtual environment activation script"
fi

# Verify we're in the virtual environment
which python
echo "Python is at: $(which python)"

# Install/update dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt  # Dev dependencies
fi

# Check for security issues (if packages installed)
if command -v pip-audit &> /dev/null; then
    pip-audit
fi
if command -v safety &> /dev/null; then
    safety check
fi

# Review recent changes
git log --oneline -20
git status
```

### 2. During Development
- Use Black for code formatting
- Run mypy for type checking
- Write docstrings for all functions/classes
- Keep requirements.txt updated
- Follow PEP 8 style guide
- Write tests using pytest

### 3. Documentation Standards
**Always update:**
- Docstrings when changing function signatures
- README.md for new dependencies or setup steps
- API documentation (Sphinx/MkDocs)
- Type hints for better code clarity
- CHANGELOG.md for new features/fixes

## Authorized Commands

### Python & Package Management
```bash
# Virtual environment
python -m venv venv
source venv/bin/activate
deactivate
pip install virtualenv
virtualenv venv

# Package management
pip install package-name
pip install -r requirements.txt
pip install -e .  # Install in editable mode
pip uninstall package-name
pip freeze > requirements.txt
pip list
pip show package-name
pip search package-name  # Note: Currently disabled on PyPI

# Upgrade packages
pip install --upgrade package-name
pip install --upgrade pip
pip-review --auto  # Requires pip-review package

# Development dependencies
pip install black flake8 mypy pytest pytest-cov
pip install ipython ipdb
pip install pre-commit
```

### Code Quality & Formatting
```bash
# Black (formatter)
black .
black src/
black --check .
black --diff .

# Flake8 (linter)
flake8 .
flake8 src/
flake8 --statistics
flake8 --count --exit-zero --max-complexity=10

# Pylint
pylint src/
pylint --rcfile=.pylintrc src/

# isort (import sorting)
isort .
isort --check-only .
isort --diff .

# mypy (type checking)
mypy .
mypy src/
mypy --strict src/
mypy --ignore-missing-imports src/

# Combined
black . && isort . && flake8 . && mypy .
```

### Testing
```bash
# pytest
pytest
pytest -v  # Verbose
pytest -s  # Show print statements
pytest --cov=src  # Coverage
pytest --cov=src --cov-report=html
pytest -k "test_name"  # Run specific test
pytest path/to/test_file.py
pytest -x  # Stop on first failure
pytest --lf  # Run last failed
pytest --ff  # Run failed first
pytest -n 4  # Parallel execution (requires pytest-xdist)

# unittest (if used)
python -m unittest discover
python -m unittest tests.test_module

# Coverage
coverage run -m pytest
coverage report
coverage html
coverage xml
```

### Running & Debugging
```bash
# Run scripts
python script.py
python -m module_name
python -c "print('Hello')"

# Interactive mode
python
ipython
python -i script.py  # Run then drop to REPL

# Debugging
python -m pdb script.py
python -m ipdb script.py  # Enhanced debugger
python -m trace -t script.py  # Trace execution

# Profiling
python -m cProfile script.py
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats

# Memory profiling
python -m memory_profiler script.py  # Requires memory-profiler
```

### Framework-Specific

#### Django
```bash
# Project management
django-admin startproject project_name
python manage.py startapp app_name

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
python manage.py sqlmigrate app_name 0001
python manage.py dbshell

# Development server
python manage.py runserver
python manage.py runserver 0.0.0.0:8000
python manage.py runserver --settings=settings.dev

# Admin & shell
python manage.py createsuperuser
python manage.py shell
python manage.py shell_plus  # With django-extensions

# Static files
python manage.py collectstatic
python manage.py findstatic

# Testing
python manage.py test
python manage.py test app_name
python manage.py test --parallel
```

#### Flask
```bash
# Development
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
flask run --host=0.0.0.0 --port=5000

# Database (Flask-Migrate)
flask db init
flask db migrate -m "Migration message"
flask db upgrade
flask db downgrade

# Shell
flask shell
```

#### FastAPI
```bash
# Development
uvicorn main:app --reload
uvicorn main:app --host 0.0.0.0 --port 8000
uvicorn main:app --workers 4

# With gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Generate OpenAPI schema
python -c "import json; from main import app; print(json.dumps(app.openapi()))"
```

### Data Science & ML
```bash
# Jupyter
jupyter notebook
jupyter lab
jupyter notebook --no-browser --port=8888

# Convert notebooks
jupyter nbconvert --to script notebook.ipynb
jupyter nbconvert --to html notebook.ipynb
jupyter nbconvert --to pdf notebook.ipynb

# IPython
ipython
ipython --matplotlib
ipython -i script.py

# Common DS operations
python -m pip install pandas numpy matplotlib seaborn scikit-learn
python -m pip install torch torchvision  # PyTorch
python -m pip install tensorflow  # TensorFlow
```

### Environment & Configuration
```bash
# Environment variables
export PYTHONPATH="${PYTHONPATH}:/path/to/module"
export PYTHON_ENV=development
python -m dotenv  # Load .env file

# Python path
python -c "import sys; print(sys.path)"
python -c "import site; print(site.getsitepackages())"

# Check imports
python -c "import package_name; print(package_name.__version__)"
python -c "import package_name; print(package_name.__file__)"
```

### Build & Distribution
```bash
# Setup tools
python setup.py sdist bdist_wheel
python setup.py install
python setup.py develop  # Install in development mode

# Build with modern tools
pip install build
python -m build

# Upload to PyPI
pip install twine
twine check dist/*
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
twine upload dist/*
```

### Documentation
```bash
# Sphinx
sphinx-quickstart
sphinx-build -b html docs/source/ docs/build/
sphinx-autobuild docs/source/ docs/build/

# MkDocs
mkdocs new project-name
mkdocs serve
mkdocs build
mkdocs gh-deploy

# Generate docs from docstrings
pdoc --html --output-dir docs src/
pydoc -w module_name
```

### Git Workflow for Python
```bash
# Feature development
git checkout -b feature/add-new-model
source venv/bin/activate
pip install -r requirements.txt

# Before committing
black .
isort .
flake8 .
mypy .
pytest

# Commit with conventional commits
git add .
git commit -m "feat(models): add user authentication model"
git commit -m "fix(api): resolve datetime serialization issue"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(auth): add unit tests for login flow"
git commit -m "chore(deps): update requirements.txt"
```

### Performance & Profiling
```bash
# Time execution
python -m timeit "code to time"
python -m timeit -s "import module" "module.function()"

# Profile code
python -m cProfile -s cumulative script.py
python -m line_profiler script.py  # Requires line-profiler
python -m memory_profiler script.py  # Requires memory-profiler

# Benchmark
python -m pytest --benchmark-only  # Requires pytest-benchmark
```

### Security & Best Practices
```bash
# Security scanning
bandit -r src/
safety check
pip-audit

# Code complexity
radon cc src/ -a  # Cyclomatic complexity
radon mi src/  # Maintainability index

# License checking
pip-licenses
pip-licenses --format=markdown
```

## Configuration Files

### pyproject.toml
```toml
[tool.black]
line-length = 88
target-version = ['py38']

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8
```

### Performance Optimization through Concurrency
When working on tasks that involve multiple independent operations:
1. **Always use subagents (Task tool) for parallel execution** when possible
2. **Launch multiple agents concurrently** for tasks like:
   - Searching for different patterns or files simultaneously
   - Analyzing multiple components independently
   - Performing batch operations on different parts of the codebase
3. **Maximize performance** by identifying tasks that can run in parallel
4. **Avoid sequential operations** when concurrent execution is possible
5. **Example scenarios for concurrent subagents:**
   - Searching for multiple keywords across the codebase
   - Reading and analyzing multiple configuration files
   - Checking different directories for specific patterns
   - Running independent analysis tasks

## Quick Reference

### Daily Commands
```bash
source venv/bin/activate  # Activate environment
python main.py           # Run application
pytest                   # Run tests
black . && flake8 .     # Format and lint
git status              # Check changes
```

### Emergency Commands
```bash
pip cache purge  # Clear pip cache
python -m venv venv --clear  # Recreate venv
pip install --force-reinstall package-name
find . -type d -name __pycache__ -exec rm -rf {} +  # Clear pycache
```

## Notes
- Always use virtual environments
- Keep requirements.txt and requirements-dev.txt separate
- Use type hints for better code clarity
- Document all environment variables in .env.example
- Run tests before committing
- Follow PEP 8 style guide