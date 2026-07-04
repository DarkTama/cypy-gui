from typing import Literal, Optional
from PIL.Image import Image

from cypy.core.providers.base import LLMProvider
from cypy.core.config import REQUEST_TIMEOUT

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using the google-genai SDK.
    Extracted from the original `utils.py` implementation~ ♪
    """

    @property
    def provider_name(self, /) -> Literal["Google Gemini"]:
        return "Google Gemini"

    def translate_image(self, /, image: Image, prompt: str) -> Optional[str]:
        if genai is None:
            raise ImportError(
                "google-genai package is not installed. "
                "Install it with: pip install google-genai"
            )

        client = genai.Client(api_key=self.api_key)
        model_config = {
            "temperature": 0,
            "top_p": 0.1,
            "top_k": 1,
            "response_mime_type": "application/json",
            "http_options": {
                "timeout": REQUEST_TIMEOUT * 1000  # in milliseconds
            }
        }
        model_config_types = None \
            if types is None      \
            else types.GenerateContentConfig(**model_config)

        # Try with full config first, fallback if library version doesn't support it~
        if types is not None:
            retries = 2
            while retries > 0:
                # First attempt we will use `response_mime_type`, if that fails,
                # the second attempt will remove that and set it to None in config
                used_config = model_config_types \
                    if retries == 2              \
                    else types.GenerateContentConfig(**model_config, response_mime_type=None)
                retries -= 1  # Decrease the retries count here before try-catch block

                try:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=[image, prompt],
                        config=used_config
                    )
                    return response.text
                except Exception as e:
                    self._check_api_key_error(e)
                    continue

        # Final fallback without types
        retries = 2
        while retries > 0:
            # Use the config during first attempt, set to None for next attempt if error
            used_config = model_config if retries == 2 else None
            retries -= 1  # Decrease the retries count here before try-catch block

            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=[image, prompt],
                    config=used_config # pyright: ignore[reportArgumentType]
                )
                return response.text
            except Exception as e:
                self._check_api_key_error(e)
                if retries > 0: continue
                raise e

    @staticmethod
    def _check_api_key_error(err: Exception) -> None:
        """Check if an error is related to API key issues and raise `ValueError` if so."""
        err_str = str(err).lower()
        if any(keyword in err_str for keyword in [
            "api key expired", "api_key_invalid", "api key", "api_key"
        ]):
            raise ValueError("API_KEY_ERROR")
