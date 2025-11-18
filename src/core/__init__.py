"""
Core components for the literature review system.

Provides the foundational architecture including configuration management,
LLM abstraction, and base agent classes.
"""

from .config import get_config, ConfigManager
from .llm_interface import get_llm_manager, LLMMessage, MessageRole, LLMResponse
from .base_agent import BaseAgent, SequentialAgent, ParallelAgent, TaskResult

__all__ = [
    'get_config',
    'ConfigManager',
    'get_llm_manager', 
    'LLMMessage',
    'MessageRole',
    'LLMResponse',
    'BaseAgent',
    'SequentialAgent',
    'ParallelAgent',
    'TaskResult'
]