# Testing Guide

## Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm test:watch

# Coverage
npm test:coverage
```

## Test Structure

```
tests/
├── unit/        # Unit tests
├── integration/ # Integration tests
└── e2e/        # End-to-end tests
```

## Writing Tests

Example test:
```javascript
describe('Component', () => {
  it('should do something', () => {
    // Test implementation
  });
});
```

## Test Coverage

Minimum coverage targets:
- Statements: 80%
- Branches: 70%
- Functions: 80%

---
Last updated: [Date]