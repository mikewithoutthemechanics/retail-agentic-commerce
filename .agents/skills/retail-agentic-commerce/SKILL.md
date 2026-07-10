```markdown
# retail-agentic-commerce Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `retail-agentic-commerce` Python codebase. It covers file naming, import/export styles, commit message conventions, and testing patterns. By following these guidelines, contributors can write consistent, maintainable code and collaborate effectively within the project.

## Coding Conventions

### File Naming
- **Pattern:** camelCase
- **Example:**  
  ```plaintext
  productManager.py
  orderProcessor.py
  ```

### Import Style
- **Pattern:** Relative imports
- **Example:**  
  ```python
  from .utils import calculateDiscount
  from .models import Order
  ```

### Export Style
- **Pattern:** Named exports (explicitly specifying what is exported)
- **Example:**  
  ```python
  __all__ = ['Order', 'Product']
  ```

### Commit Messages
- **Pattern:** Conventional commits, using the `feat` prefix for features.
- **Example:**  
  ```
  feat: add inventory check to order processing
  ```

## Workflows

### Adding a New Feature
**Trigger:** When implementing a new feature or module  
**Command:** `/add-feature`

1. Create a new file using camelCase naming (e.g., `newFeature.py`).
2. Use relative imports to include any dependencies.
3. Export key classes or functions using `__all__`.
4. Write a test file named `newFeature.test.py` for your feature.
5. Commit your changes using a conventional commit message:
   ```
   feat: short description of the feature
   ```

### Writing and Running Tests
**Trigger:** When validating new or existing code  
**Command:** `/run-tests`

1. Write test files using the `*.test.*` naming pattern (e.g., `orderProcessor.test.py`).
2. Use your preferred Python testing framework (none detected, so choose one like `pytest` or `unittest`).
3. Run your tests using the appropriate command for your chosen framework.
4. Ensure all tests pass before submitting code.

## Testing Patterns

- **Test File Naming:**  
  Use the `*.test.*` pattern, such as `cartManager.test.py`.
- **Framework:**  
  No specific framework detected. You may use `pytest`, `unittest`, or another Python test runner.
- **Example Test File:**  
  ```python
  # orderProcessor.test.py
  from .orderProcessor import processOrder

  def test_processOrder_success():
      # Arrange
      order = {...}
      # Act
      result = processOrder(order)
      # Assert
      assert result['status'] == 'success'
  ```

## Commands
| Command        | Purpose                                      |
|----------------|----------------------------------------------|
| /add-feature   | Scaffold and commit a new feature/module     |
| /run-tests     | Run all test files in the codebase           |
```
