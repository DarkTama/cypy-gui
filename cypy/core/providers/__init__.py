from typing import cast, overload, Dict, Literal, Union, Type, TypeAlias

from cypy.core.types import AnyDict
from cypy.core.providers.base import APIKey, LLMProvider
from cypy.core.providers.gemini import GeminiProvider
from cypy.core.providers.openrouter import OpenRouterProvider
from cypy.core.providers.openai import OpenAIProvider
from cypy.core.providers.zen import ZenProvider
from cypy.core.providers.custom import CustomProvider

ProviderNames: TypeAlias = Literal[
    # Please add the key manually if updating the `PROVIDER_MAP` dictionary above
    "gemini", "openai", "zen", "openrouter", "custom"
]

PROVIDER_MAP: Dict[ProviderNames, Type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "zen": ZenProvider,
    "openrouter": OpenRouterProvider,
    "custom": CustomProvider,
}


@overload
def create_provider(provider_name: Literal["gemini"], /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> GeminiProvider: ...
@overload
def create_provider(provider_name: Literal["openai"], /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> OpenAIProvider: ...
@overload
def create_provider(provider_name: Literal["zen"], /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> ZenProvider: ...
@overload
def create_provider(provider_name: Literal["openrouter"], /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> OpenRouterProvider: ...
@overload
def create_provider(provider_name: Literal["custom"], /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> CustomProvider: ...
@overload
def create_provider(provider_name: str, /, api_key: APIKey, model_name: str, **kwargs: AnyDict) -> LLMProvider: ...

def create_provider(
    provider_name: Union[ProviderNames, str],
    /,
    api_key: APIKey,
    model_name: str,
    **kwargs: AnyDict
) -> LLMProvider:
    # We need to cast the str type first here
    cls = PROVIDER_MAP.get(cast(ProviderNames, provider_name))
    if cls is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(api_key=api_key, model_name=model_name, **kwargs)
