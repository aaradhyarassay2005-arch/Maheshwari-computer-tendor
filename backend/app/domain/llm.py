from abc import ABC, abstractmethod


class ILLMProvider(ABC):
    """Abstraction for LLM provider to ensure pluggability of different AI models."""

    @abstractmethod
    async def generate_response(self, system_instruction: str, prompt: str) -> str:
        """Sends a system instruction and user prompt to the LLM and returns the text response."""
        pass
