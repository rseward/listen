import pytest
import os
from unittest.mock import patch, MagicMock, Mock
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from listen_tools.text_improver import TextImprover, gemini_available, ollama_available


class TestGeminiAvailable:
    """Test the gemini_available function"""

    def test_gemini_available_no_api_key(self):
        """Test gemini_available returns False when no API key is set"""
        with patch.dict(os.environ, {}, clear=True):
            assert gemini_available() is False

    def test_gemini_available_with_api_key(self):
        """Test gemini_available returns True when API key is set and import succeeds"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            # Test with real module if available, otherwise test behavior
            result = gemini_available()
            # Should return True if API key is set (real module handles configure)
            assert result is True

    def test_gemini_available_import_error(self):
        """Test gemini_available returns False when import fails"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            with patch('builtins.__import__', side_effect=ImportError):
                assert gemini_available() is False

    def test_gemini_available_exception_on_configure(self):
        """Test gemini_available returns False when configure raises exception"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            # Patch the configure function to raise an exception
            with patch('google.generativeai.configure', side_effect=Exception("API error")):
                assert gemini_available() is False


class TestOllamaAvailable:
    """Test the ollama_available function"""

    def test_ollama_available_success(self):
        """Test ollama_available returns True when Ollama is running"""
        with patch('listen_tools.text_improver.httpx.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"models": []}'
            mock_get.return_value = mock_response

            assert ollama_available() is True
            mock_get.assert_called_once()

    def test_ollama_available_custom_base_url(self):
        """Test ollama_available uses custom base URL from environment"""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://custom:8080/api"}):
            with patch('listen_tools.text_improver.httpx.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = '{"models": []}'
                mock_get.return_value = mock_response

                assert ollama_available() is True
                mock_get.assert_called_with("http://custom:8080/api/tags", timeout=5)

    def test_ollama_available_connection_error(self):
        """Test ollama_available returns False when connection fails"""
        with patch('listen_tools.text_improver.httpx.get', side_effect=Exception("Connection failed")):
            assert ollama_available() is False

    def test_ollama_available_non_200_status(self):
        """Test ollama_available returns False when status is not 200"""
        with patch('listen_tools.text_improver.httpx.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            assert ollama_available() is False


class TestTextImprover:
    """Test the TextImprover class"""

    def test_init_with_gemini(self):
        """Test TextImprover initializes with Gemini when available"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                improver = TextImprover("Test prompt")

                assert improver.model == "google:models/gemini-2.0-flash-exp"
                assert improver.prompt == "Test prompt"

    def test_init_with_ollama(self):
        """Test TextImprover initializes with Ollama when Gemini not available"""
        with patch('listen_tools.text_improver.gemini_available', return_value=False):
            with patch('listen_tools.text_improver.ollama_available', return_value=True):
                improver = TextImprover("Test prompt")

                assert improver.model == "ollama:gemma3:latest"
                assert improver.prompt == "Test prompt"

    def test_init_with_no_service(self):
        """Test TextImprover initializes with no model when no service available"""
        with patch('listen_tools.text_improver.gemini_available', return_value=False):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                improver = TextImprover("Test prompt")

                assert improver.model is None
                assert improver.prompt == "Test prompt"

    def test_init_with_base_url(self):
        """Test TextImprover sets base_url from environment"""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://custom:8080"}):
            with patch('listen_tools.text_improver.gemini_available', return_value=False):
                with patch('listen_tools.text_improver.ollama_available', return_value=False):
                    improver = TextImprover("Test prompt")

                    assert improver.base_url == "http://custom:8080"

    def test_improve_with_base_url(self):
        """Test improve method with base_url set"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://custom:8080"}):
                    with patch('listen_tools.text_improver.any_llm.completion') as mock_completion:
                        # Mock the response
                        mock_response = MagicMock()
                        mock_response.choices = [MagicMock()]
                        mock_response.choices[0].message.content = "Improved text"
                        mock_completion.return_value = mock_response

                        improver = TextImprover("Fix grammar")
                        result = improver.improve("test text")

                        assert result == "Improved text"
                        mock_completion.assert_called_once_with(
                            model="google:models/gemini-2.0-flash-exp",
                            messages=[
                                {"role": "system", "content": "Fix grammar"},
                                {"role": "user", "content": "test text"}
                            ],
                            api_base="http://custom:8080"
                        )

    def test_improve_without_base_url(self):
        """Test improve method without base_url"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    with patch('listen_tools.text_improver.any_llm.completion') as mock_completion:
                        # Mock the response
                        mock_response = MagicMock()
                        mock_response.choices = [MagicMock()]
                        mock_response.choices[0].message.content = "Better text"
                        mock_completion.return_value = mock_response

                        improver = TextImprover("Improve this")
                        result = improver.improve("original text")

                        assert result == "Better text"
                        mock_completion.assert_called_once_with(
                            model="google:models/gemini-2.0-flash-exp",
                            messages=[
                                {"role": "system", "content": "Improve this"},
                                {"role": "user", "content": "original text"}
                            ]
                        )

    def test_improve_returns_original_on_none_response(self):
        """Test improve returns original text when response is None"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                with patch('listen_tools.text_improver.any_llm.completion', return_value=None):
                    improver = TextImprover("Fix this")
                    result = improver.improve("original text")

                    assert result == "original text"

    def test_improve_handles_different_prompts(self):
        """Test improve method works with different prompts"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                with patch('listen_tools.text_improver.any_llm.completion') as mock_completion:
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = "Punctuated text."
                    mock_completion.return_value = mock_response

                    improver = TextImprover("Add punctuation")
                    result = improver.improve("test text")

                    assert result == "Punctuated text."
                    # Verify the system message contains the custom prompt
                    call_args = mock_completion.call_args
                    assert call_args[1]['messages'][0]['content'] == "Add punctuation"

    def test_improve_with_empty_text(self):
        """Test improve method with empty text"""
        with patch('listen_tools.text_improver.gemini_available', return_value=True):
            with patch('listen_tools.text_improver.ollama_available', return_value=False):
                with patch('listen_tools.text_improver.any_llm.completion') as mock_completion:
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = ""
                    mock_completion.return_value = mock_response

                    improver = TextImprover("Test prompt")
                    result = improver.improve("")

                    assert result == ""
                    # Verify empty text was passed
                    call_args = mock_completion.call_args
                    assert call_args[1]['messages'][1]['content'] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
