# Scheduler Test Suite

This directory contains comprehensive test cases for the scheduler system, covering all components with edge cases, error scenarios, and performance tests.

## 📁 Test Files Overview

### Core Test Files

- **`test_scheduler.py`** - Main scheduler component tests
  - SchedulerService tests
  - ChangeDetector tests  
  - AlertManager tests
  - FingerprintManager tests
  - ReportGenerator tests
  - Integration tests

- **`test_scheduler_models.py`** - Data model tests
  - ChangeType and ChangeSeverity enums
  - ContentFingerprint model
  - ChangeLog model
  - ChangeDetectionResult model
  - AlertConfig and SchedulerConfig models
  - DailyReport model
  - Serialization/deserialization tests

- **`test_scheduler_edge_cases.py`** - Edge cases and error scenarios
  - Extreme data values
  - Unicode and special characters
  - Boundary conditions
  - Error handling scenarios
  - Concurrency edge cases
  - Memory edge cases
  - Network error scenarios

- **`test_scheduler_performance.py`** - Performance and memory tests
  - Fingerprint generation performance
  - Change detection performance
  - Alert manager performance
  - Concurrent operations performance
  - Memory leak detection
  - Large dataset handling

### Supporting Files

- **`conftest.py`** - Shared fixtures and test configuration
- **`run_scheduler_tests.py`** - Test runner script with multiple options

## 🧪 Test Categories

### 1. Unit Tests
- Individual component testing
- Model validation
- Method functionality
- Error handling

### 2. Integration Tests
- Component interaction testing
- End-to-end workflows
- Database integration
- Service orchestration

### 3. Edge Case Tests
- Boundary value testing
- Invalid input handling
- Extreme data scenarios
- Error recovery

### 4. Performance Tests
- Speed benchmarks
- Memory usage monitoring
- Concurrent operation testing
- Large dataset handling

### 5. Error Scenario Tests
- Network failures
- Database errors
- Malformed data
- Timeout handling

## 🚀 Running Tests

### Quick Start

```bash
# Run all scheduler tests
python run_scheduler_tests.py all

# Run quick tests (no performance tests)
python run_scheduler_tests.py quick

# Run with coverage report
python run_scheduler_tests.py coverage
```

### Individual Test Suites

```bash
# Core scheduler tests
python run_scheduler_tests.py core

# Model validation tests
python run_scheduler_tests.py models

# Edge cases and error scenarios
python run_scheduler_tests.py edge

# Performance tests only
python run_scheduler_tests.py performance
```

### Direct pytest Commands

```bash
# Run specific test file
pytest tests/test_scheduler.py -v

# Run specific test class
pytest tests/test_scheduler.py::TestSchedulerService -v

# Run specific test method
pytest tests/test_scheduler.py::TestSchedulerService::test_start_scheduler_success -v

# Run with coverage
pytest tests/test_scheduler.py --cov=scheduler --cov-report=html
```

## 📊 Test Coverage

The test suite covers:

### ✅ SchedulerService
- Startup and shutdown
- Run-once mode
- Test mode
- Database connection handling
- Job scheduling
- Manual change detection
- Status reporting

### ✅ ChangeDetector
- Change detection logic
- Fingerprint comparison
- New book detection
- Removed book detection
- Batch processing
- Error handling
- Database operations

### ✅ AlertManager
- Change processing
- Severity filtering
- Rate limiting
- Cooldown periods
- Log alerting
- Error handling

### ✅ FingerprintManager
- Fingerprint storage
- Fingerprint retrieval
- Fingerprint updates
- Database operations
- Error handling

### ✅ ContentFingerprinter
- Book ID generation
- Fingerprint generation
- Fingerprint comparison
- Field change detection
- Hash generation

### ✅ ReportGenerator
- Daily report generation
- Report cleanup
- Data aggregation
- Export functionality
- Error handling

### ✅ Data Models
- Validation rules
- Serialization
- Deserialization
- Edge cases
- Type checking

## 🔍 Test Scenarios

### Normal Operations
- Valid data processing
- Successful change detection
- Proper alert generation
- Report creation
- Database operations

### Error Scenarios
- Database connection failures
- Network timeouts
- Invalid data formats
- Missing required fields
- Malformed URLs
- Invalid enum values

### Edge Cases
- Empty datasets
- Very large datasets
- Unicode characters
- Special characters
- Boundary time values
- Extreme numeric values

### Performance Scenarios
- Large book collections (10,000+ books)
- High-frequency changes
- Concurrent operations
- Memory usage monitoring
- Processing speed benchmarks

## 🛠️ Test Fixtures

### Shared Fixtures (conftest.py)
- `scheduler_config` - Scheduler configuration
- `alert_config` - Alert configuration
- `sample_change_log` - Sample change log
- `sample_content_fingerprint` - Sample fingerprint
- `sample_change_detection_result` - Sample detection result
- `mock_scheduler_db_manager` - Mock database manager

### Test-Specific Fixtures
- Mock data generators
- Error simulators
- Performance measurement tools
- Memory monitoring utilities

## 📈 Performance Benchmarks

### Expected Performance Targets

| Operation | Target | Test Dataset |
|-----------|--------|--------------|
| Fingerprint Generation | < 0.1s per book | 1,000 books |
| Change Detection | < 30s | 10,000 books |
| Alert Processing | < 5s | 10,000 changes |
| Report Generation | < 2s | Daily report |
| Concurrent Operations | < 10s | 10 concurrent tasks |

### Memory Usage Limits

| Component | Memory Limit | Test Scenario |
|-----------|--------------|---------------|
| Fingerprint Generation | < 100MB | 10,000 fingerprints |
| Change Detection | < 200MB | 5,000 books |
| Alert Processing | < 100MB | 5,000 changes |
| Overall System | < 500MB | Full workflow |

## 🐛 Debugging Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source path/to/venv/bin/activate
   ```

2. **Database Connection Errors**
   - Tests use mocks, no real database needed
   - Check mock setup in fixtures

3. **Performance Test Failures**
   - May fail on slower systems
   - Adjust performance thresholds if needed

4. **Memory Test Failures**
   - May fail on systems with limited memory
   - Reduce test dataset sizes if needed

### Debug Mode

```bash
# Run with detailed output
pytest tests/test_scheduler.py -v -s

# Run with debug logging
pytest tests/test_scheduler.py --log-cli-level=DEBUG

# Run single test with debugging
pytest tests/test_scheduler.py::TestSchedulerService::test_start_scheduler_success -v -s --pdb
```

## 📝 Adding New Tests

### Test Structure

```python
class TestNewComponent:
    """Test cases for new component."""
    
    @pytest.fixture
    def component_instance(self):
        """Create component instance for testing."""
        return NewComponent()
    
    def test_valid_operation(self, component_instance):
        """Test valid operation."""
        result = component_instance.valid_operation()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_async_operation(self, component_instance):
        """Test async operation."""
        result = await component_instance.async_operation()
        assert result is not None
    
    def test_error_handling(self, component_instance):
        """Test error handling."""
        with pytest.raises(ValueError):
            component_instance.invalid_operation()
```

### Test Naming Conventions

- Test classes: `TestComponentName`
- Test methods: `test_operation_scenario`
- Fixtures: `component_instance`, `sample_data`
- Async tests: Use `@pytest.mark.asyncio`

### Test Categories

- **Unit Tests**: Test individual methods
- **Integration Tests**: Test component interactions
- **Edge Cases**: Test boundary conditions
- **Error Scenarios**: Test error handling
- **Performance Tests**: Test speed and memory usage

## 🔧 Configuration

### Test Configuration

Tests use the following configuration:
- **AsyncIO**: For async/await testing
- **Pytest**: Main testing framework
- **Pytest-AsyncIO**: For async test support
- **Unittest.mock**: For mocking dependencies
- **Psutil**: For memory monitoring (performance tests)

### Environment Variables

```bash
# Optional: Set test database URL
export TEST_MONGODB_URL="mongodb://localhost:27017/test_db"

# Optional: Set log level
export TEST_LOG_LEVEL="DEBUG"
```

## 📊 Test Reports

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=scheduler --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Performance Reports

Performance tests generate timing and memory usage reports:
- Execution times for operations
- Memory usage patterns
- Concurrent operation performance
- Memory leak detection results

## 🎯 Test Goals

### Primary Goals
- ✅ 100% code coverage for scheduler components
- ✅ All edge cases covered
- ✅ Performance benchmarks met
- ✅ Error scenarios handled
- ✅ Integration workflows tested

### Quality Assurance
- ✅ No memory leaks
- ✅ Proper error handling
- ✅ Graceful degradation
- ✅ Concurrent operation safety
- ✅ Data validation

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [AsyncIO Testing](https://docs.python.org/3/library/asyncio-testing.html)
- [Pytest-AsyncIO](https://pytest-asyncio.readthedocs.io/)
- [Unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

**Note**: This test suite is designed to be comprehensive and maintainable. When adding new features to the scheduler, ensure corresponding tests are added to maintain coverage and quality.

