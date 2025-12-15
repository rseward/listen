import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from listen_tools.text_improver import TextImprover, gemini_available, ollama_available


# Integration tests that connect to real services
# Run with: pytest tests/test_text_improver_integration.py -v -m integration
# Skip with: pytest tests/ -v -m "not integration"


@pytest.mark.integration
class TestGeminiIntegration:
    """Integration tests for Gemini API"""

    def test_gemini_service_available(self):
        """Test if Gemini service is actually available"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        assert gemini_available() is True

    def test_gemini_text_improvement(self):
        """Test actual text improvement with Gemini"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available():
            pytest.skip("Gemini not available")

        prompt = "Fix grammar and punctuation in the following text:"
        improver = TextImprover(prompt)

        # Test with simple text that needs improvement
        input_text = "this is a test with bad grammar and no punctuation"
        result = improver.improve(input_text)

        # Verify we got a response
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, str)

        # The improved text should be different (hopefully capitalized and punctuated)
        # But we can't be too strict since LLM output varies
        print(f"\nOriginal: {input_text}")
        print(f"Improved: {result}")

    def test_gemini_transcription_improvement(self):
        """Test improving transcribed text with Gemini"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available():
            pytest.skip("Gemini not available")

        prompt = """You are helping to clean up audio transcriptions.
Fix grammar, add punctuation, and make the text more readable.
Only return the improved text without any explanation."""

        improver = TextImprover(prompt)

        # Simulate transcribed speech (often lacks punctuation)
        transcribed_text = "um so i was thinking maybe we could uh you know go to the store later and pick up some groceries"
        result = improver.improve(transcribed_text)

        assert result is not None
        assert len(result) > 0
        print(f"\nTranscribed: {transcribed_text}")
        print(f"Cleaned up: {result}")

    def test_gemini_empty_text(self):
        """Test Gemini with empty text"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available():
            pytest.skip("Gemini not available")

        improver = TextImprover("Improve this text:")
        result = improver.improve("")

        # Should handle empty text gracefully
        assert result is not None
        assert isinstance(result, str)

    def test_gemini_with_custom_base_url(self):
        """Test Gemini with custom base URL if set"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available():
            pytest.skip("Gemini not available")

        # This test checks if custom base URL works
        improver = TextImprover("Fix this text:")
        result = improver.improve("test message")

        assert result is not None
        assert isinstance(result, str)
        print(f"\nBase URL used: {improver.base_url}")
        print(f"Model: {improver.model}")


@pytest.mark.integration
class TestOllamaIntegration:
    """Integration tests for Ollama API"""

    def test_ollama_service_available(self):
        """Test if Ollama service is actually running"""
        is_available = ollama_available()

        if not is_available:
            pytest.skip("Ollama not running on localhost:11434")

        assert is_available is True

    def test_ollama_text_improvement(self):
        """Test actual text improvement with Ollama"""
        if not ollama_available():
            pytest.skip("Ollama not running")

        prompt = "Fix grammar and punctuation in the following text:"

        # Force Ollama by ensuring Gemini is not available
        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)
            improver = TextImprover(prompt)

            # Verify we're using Ollama
            assert improver.model is not None
            assert "ollama" in improver.model.lower()

            # Test with simple text
            input_text = "this is a test with bad grammar and no punctuation"
            result = improver.improve(input_text)

            assert result is not None
            assert len(result) > 0
            assert isinstance(result, str)

            print(f"\nOriginal: {input_text}")
            print(f"Improved (Ollama): {result}")

    def test_ollama_transcription_cleanup(self):
        """Test cleaning up transcribed audio with Ollama"""
        if not ollama_available():
            pytest.skip("Ollama not running")

        prompt = """Clean up this audio transcription.
Remove filler words (um, uh, you know), fix grammar, and add punctuation.
Return only the cleaned text."""

        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)
            improver = TextImprover(prompt)

            transcribed = "um i think uh we should probably you know uh go to the meeting at three"
            result = improver.improve(transcribed)

            assert result is not None
            assert len(result) > 0
            print(f"\nOriginal transcription: {transcribed}")
            print(f"Cleaned (Ollama): {result}")

    def test_ollama_with_custom_base_url(self):
        """Test Ollama with custom base URL"""
        if not ollama_available():
            pytest.skip("Ollama not running")

        custom_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/api")

        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)
            # Set the base URL before creating improver
            m.setenv("OPENAI_BASE_URL", custom_url)
            improver = TextImprover("Test prompt")

            # base_url should be set from environment
            print(f"\nOllama base URL: {improver.base_url}")
            print(f"Model: {improver.model}")

            # Just verify the configuration, don't try to use a model that might not exist
            assert improver.base_url == custom_url
            assert improver.model is not None


@pytest.mark.integration
class TestTextImproverServiceSelection:
    """Integration tests for service selection logic"""

    def test_prefers_gemini_when_both_available(self):
        """Test that Gemini is preferred when both services are available"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available() or not ollama_available():
            pytest.skip("Both Gemini and Ollama must be available")

        improver = TextImprover("Test prompt")

        # Should prefer Gemini
        assert improver.model is not None
        assert "gemini" in improver.model.lower()

    def test_falls_back_to_ollama(self):
        """Test fallback to Ollama when Gemini is not available"""
        if not ollama_available():
            pytest.skip("Ollama not running")

        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)
            improver = TextImprover("Test prompt")

            # Should use Ollama
            assert improver.model is not None
            assert "ollama" in improver.model.lower()

    def test_handles_no_service_available(self):
        """Test behavior when no AI service is available"""
        from unittest.mock import patch

        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)

            # Mock both services to return False
            with patch('listen_tools.text_improver.gemini_available', return_value=False):
                with patch('listen_tools.text_improver.ollama_available', return_value=False):
                    improver = TextImprover("Test prompt")

                    # Model should be None
                    assert improver.model is None

                    # Should return original text when improving
                    original = "test text"
                    result = improver.improve(original)
                    assert result == original


@pytest.mark.integration
@pytest.mark.slow
class TestTextImproverPerformance:
    """Performance tests for TextImprover"""

    def test_gemini_response_time(self):
        """Test Gemini API response time"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        if not gemini_available():
            pytest.skip("Gemini not available")

        import time

        improver = TextImprover("Fix this text:")

        start = time.time()
        result = improver.improve("this is a test")
        elapsed = time.time() - start

        assert result is not None
        print(f"\nGemini response time: {elapsed:.2f}s")

        # Reasonable timeout (should respond within 30 seconds)
        assert elapsed < 30.0

    def test_ollama_response_time(self):
        """Test Ollama API response time"""
        if not ollama_available():
            pytest.skip("Ollama not running")

        import time

        with pytest.MonkeyPatch.context() as m:
            m.delenv("GEMINI_API_KEY", raising=False)
            improver = TextImprover("Fix this text:")

            start = time.time()
            result = improver.improve("this is a test")
            elapsed = time.time() - start

            assert result is not None
            print(f"\nOllama response time: {elapsed:.2f}s")

            # Ollama can be slower depending on hardware
            assert elapsed < 60.0

    def test_batch_improvements(self):
        """Test improving multiple texts in sequence"""
        # Use whichever service is available
        if os.getenv("GEMINI_API_KEY") and gemini_available():
            service = "Gemini"
        elif ollama_available():
            service = "Ollama"
            # Clear Gemini key to force Ollama
            with pytest.MonkeyPatch.context() as m:
                m.delenv("GEMINI_API_KEY", raising=False)
        else:
            pytest.skip("No AI service available")

        improver = TextImprover("Fix grammar and punctuation:")

        test_texts = [
            "this is test one",
            "this is test two without punctuation",
            "this is test three also needs fixing"
        ]

        import time
        start = time.time()

        results = []
        for text in test_texts:
            result = improver.improve(text)
            results.append(result)
            assert result is not None
            assert len(result) > 0

        elapsed = time.time() - start

        print(f"\n{service} processed {len(test_texts)} texts in {elapsed:.2f}s")
        print(f"Average: {elapsed/len(test_texts):.2f}s per text")

        # All should complete within reasonable time
        assert len(results) == len(test_texts)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
