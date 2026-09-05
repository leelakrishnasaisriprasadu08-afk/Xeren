"""Code generation and modification tool leveraging injected LLM."""

import asyncio
import logging
import re
from typing import Optional, Sequence

from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.models.types import ChatMessage, Role
from xeren.plugins.coding.schemas import FileArtifact

logger = logging.getLogger("xeren.plugins.coding.tools.generation")


class CodeGenerationTool:
    """Coordinates code generation, editing, and refactoring using the active LLM."""

    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        self.llm = llm or MockLLM()

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject or update the active LLM provider."""
        self.llm = llm

    @staticmethod
    def extract_code_block(text: str, language: str = "python") -> str:
        """Extract code from markdown code fences or return raw cleaned text."""
        # Match ```python ... ``` or ``` ... ```
        pattern = rf"```(?:{re.escape(language)}|[\w\-]+)?\s*\n([\s\S]*?)\n```"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback to general code fence
        generic_match = re.search(r"```\s*\n([\s\S]*?)\n```", text)
        if generic_match:
            return generic_match.group(1).strip()

        return text.strip()

    def generate(
        self,
        task: str,
        language: str = "python",
        context_files: Optional[Sequence[FileArtifact]] = None,
    ) -> str:
        """Generate code satisfying the specified task and language."""
        context_str = ""
        if context_files:
            file_blocks = [f"# File: {f.file_path}\n{f.content}" for f in context_files]
            context_str = "\n\nExisting Context Files:\n" + "\n\n".join(file_blocks)

        prompt = (
            f"You are an expert software engineer. Implement the following coding task in {language}.\n"
            f"Task: {task}\n"
            f"{context_str}\n"
            "Return only the complete, functional code wrapped in markdown code fences."
        )

        messages = [
            ChatMessage(role=Role.SYSTEM, content=f"You write clean, secure, production-grade {language} code."),
            ChatMessage(role=Role.USER, content=prompt),
        ]

        response = self.llm.generate(messages)
        raw_text = response.content

        # Graceful fallback when using default unconfigured MockLLM
        if raw_text.startswith("Mock response to:"):
            if language.lower() == "python":
                return f"# Solution for: {task}\ndef solution():\n    return True\n"
            return f"// Solution for: {task}\nfunction solution() {{ return true; }}\n"

        return self.extract_code_block(raw_text, language=language)

    async def agenerate(
        self,
        task: str,
        language: str = "python",
        context_files: Optional[Sequence[FileArtifact]] = None,
    ) -> str:
        """Asynchronously generate code."""
        return await asyncio.to_thread(self.generate, task, language, context_files)

    def edit(
        self,
        task: str,
        source_code: str,
        language: str = "python",
    ) -> str:
        """Modify or refactor existing code according to instruction."""
        prompt = (
            f"You are an expert software engineer. Modify the following {language} code to satisfy this task.\n"
            f"Task: {task}\n\n"
            f"Original Code:\n```{language}\n{source_code}\n```\n\n"
            "Return only the modified code wrapped in markdown code fences."
        )

        messages = [
            ChatMessage(role=Role.SYSTEM, content=f"You refactor and edit {language} code accurately."),
            ChatMessage(role=Role.USER, content=prompt),
        ]

        response = self.llm.generate(messages)
        raw_text = response.content

        if raw_text.startswith("Mock response to:"):
            if language.lower() == "python":
                return f"# Modified solution for: {task}\n{source_code}\n"
            return f"// Modified solution for: {task}\n{source_code}\n"

        return self.extract_code_block(raw_text, language=language)

    async def aedit(
        self,
        task: str,
        source_code: str,
        language: str = "python",
    ) -> str:
        """Asynchronously modify or refactor code."""
        return await asyncio.to_thread(self.edit, task, source_code, language)


__all__ = ["CodeGenerationTool"]
