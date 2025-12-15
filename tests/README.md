# Tests Documentation

This directory contains unit tests and integration tests for the Listen project.

## Test Structure

- `test_text_improver.py` - Unit tests for TextImprover class (mocked, no external dependencies)
- `test_text_improver_integration.py` - Integration tests that connect to real AI services

## Running Tests

### Run only unit tests (default, fast)
```bash
make test
# or
make test-unit
# or
pytest tests/ -v -m "not integration"
```

### Run only integration tests (requires external services)
```bash
make test-integration
# or
pytest tests/ -v -m integration
```

### Run all tests (unit + integration)
```bash
make test-all
# or
pytest tests/ -v
```

## Integration Tests Setup

Integration tests connect to real AI services and require proper setup.

### Gemini Integration Tests

To run Gemini integration tests, you need:

1. A Google Gemini API key
2. Set the environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

Tests will automatically skip if the API key is not set.

### Ollama Integration Tests

To run Ollama integration tests, you need:

1. Ollama installed and running locally
2. Default URL: `http://localhost:11434/api`
3. Custom URL (optional):
   ```bash
   export OPENAI_BASE_URL="http://custom-host:port/api"
   ```

Tests will automatically skip if Ollama is not running.

### Setting up Ollama

```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull gemma3:latest

# Start Ollama (usually runs as a service)
ollama serve
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.integration` - Tests that connect to real external services
- `@pytest.mark.slow` - Tests that may take longer to run

### Skip integration tests
```bash
pytest tests/ -v -m "not integration"
```

### Skip slow tests
```bash
pytest tests/ -v -m "not slow"
```

### Run only integration tests
```bash
pytest tests/ -v -m integration
```

### Run only slow tests
```bash
pytest tests/ -v -m slow
```

## Integration Test Coverage

### Gemini Tests
- `test_gemini_service_available` - Verify Gemini API is accessible
- `test_gemini_text_improvement` - Test basic text improvement
- `test_gemini_transcription_improvement` - Test cleaning up transcribed audio
- `test_gemini_empty_text` - Test handling of empty input
- `test_gemini_with_custom_base_url` - Test with custom API endpoint

### Ollama Tests
- `test_ollama_service_available` - Verify Ollama is running
- `test_ollama_text_improvement` - Test basic text improvement
- `test_ollama_transcription_cleanup` - Test cleaning up transcribed audio
- `test_ollama_with_custom_base_url` - Test with custom Ollama URL

### Service Selection Tests
- `test_prefers_gemini_when_both_available` - Verify Gemini has priority
- `test_falls_back_to_ollama` - Verify Ollama fallback works
- `test_handles_no_service_available` - Test graceful degradation

### Performance Tests
- `test_gemini_response_time` - Measure Gemini API latency
- `test_ollama_response_time` - Measure Ollama API latency
- `test_batch_improvements` - Test processing multiple texts

## CI/CD Considerations

For continuous integration:

```bash
# Run only unit tests in CI (no external dependencies)
pytest tests/ -v -m "not integration"

# Run integration tests only if services are available
# (configure secrets/services in your CI environment)
pytest tests/ -v -m integration
```

## Troubleshooting

### Integration tests are skipped
- Check if required environment variables are set
- Verify services are running and accessible
- Check network connectivity

### Ollama connection errors
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama logs
journalctl -u ollama -f
```

### Gemini API errors
- Verify API key is valid
- Check API quotas and limits
- Ensure billing is enabled for your Google Cloud project

## Example Output

```
tests/test_text_improver.py::TestGeminiAvailable::test_gemini_available_no_api_key PASSED
tests/test_text_improver.py::TestTextImprover::test_init_with_gemini PASSED
...
============================== 17 passed in 0.43s ==============================

tests/test_text_improver_integration.py::TestGeminiIntegration::test_gemini_service_available PASSED
tests/test_text_improver_integration.py::TestGeminiIntegration::test_gemini_text_improvement PASSED
...
============================== 15 passed in 12.34s ==============================
```
