# Contributing to waytrans

Thank you for your interest in contributing!

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/waytrans.git
   cd waytrans
   ```

2. Test running locally:
   ```bash
   ./bin/waytrans --help
   ```

3. Code Conventions:
   - Follow standard PEP 8 conventions for Python.
   - Run syntax and formatting checks before submitting PRs:
     ```bash
     python3 -m py_compile waytrans/*.py
     ```

## Git & PR Workflow

1. Create a dedicated topic branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Write conventional commits (`feat: ...`, `fix: ...`, `docs: ...`).
3. Open pull requests targeting the `staging` branch first.
