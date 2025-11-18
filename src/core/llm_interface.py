"""
LLM Interface abstraction layer.

Provides a unified interface for multiple LLM providers (OpenAI, Anthropic,
Google, Local models) with consistent error handling, rate limiting, and
cost tracking.
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from .config import get_config, LLMProvider
from ..utils.logger import get_logger
from ..utils.exceptions import (
    LLMProviderError, AuthenticationError, RateLimitError, 
    NetworkError, ValidationError
)


class MessageRole(Enum):
    """Message role types for LLM conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """Structured message for LLM interactions."""
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Response from LLM with metadata."""
    content: str
    model: str
    provider: str
    tokens_used: int
    cost: float
    response_time: float
    finish_reason: Optional[str] = None


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""
    
    def __init__(self, provider_config: LLMProvider):
        self.config = provider_config
        self.logger = get_logger(f"llm.{provider_config.name}")
        self._last_call_time = 0
        self._call_count = 0
    
    @abstractmethod
    async def generate_response(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    def estimate_cost(self, messages: List[LLMMessage], model: str) -> float:
        """Estimate cost for the given messages."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for the given text."""
        pass
    
    def _check_rate_limit(self):
        """Check if we're within rate limits."""
        current_time = time.time()
        rate_limits = self.config.rate_limits
        
        # Check requests per minute
        if current_time - self._last_call_time < 60 / rate_limits['requests_per_minute']:
            sleep_time = 60 / rate_limits['requests_per_minute'] - (current_time - self._last_call_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self._last_call_time = time.time()
        self._call_count += 1


class OpenAIProvider(LLMProviderInterface):
    """OpenAI LLM provider implementation."""
    
    def __init__(self, provider_config: LLMProvider):
        super().__init__(provider_config)
        if not OPENAI_AVAILABLE:
            raise LLMProviderError("OpenAI library not installed")
        
        self.client = OpenAI(api_key=provider_config.api_key, base_url=provider_config.base_url)
    
    async def generate_response(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using OpenAI API."""
        self._check_rate_limit()
        
        start_time = time.time()
        
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]
            
            # Make API call
            response = self.client.chat.completions.create(
                model=kwargs.get('model', self.config.models.get('fast', 'gpt-3.5-turbo')),
                messages=openai_messages,
                temperature=kwargs.get('temperature', 0.2),
                max_tokens=kwargs.get('max_tokens', 2048),
                **{k: v for k, v in kwargs.items() if k not in ['model', 'temperature', 'max_tokens']}
            )
            
            # Calculate metrics
            response_time = time.time() - start_time
            tokens_used = response.usage.total_tokens if response.usage else 0
            cost = self.estimate_cost(messages, response.model)
            
            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider="openai",
                tokens_used=tokens_used,
                cost=cost,
                response_time=response_time,
                finish_reason=response.choices[0].finish_reason
            )
            
            self.logger.log_llm_call(
                provider="openai",
                model=response.model,
                tokens_used=tokens_used,
                cost=cost,
                task=kwargs.get('task_name', 'unknown')
            )
            
            return llm_response
            
        except openai.AuthenticationError as e:
            raise AuthenticationError(f"OpenAI authentication failed: {str(e)}", provider="openai")
        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}", provider="openai")
        except openai.APIError as e:
            raise LLMProviderError(f"OpenAI API error: {str(e)}", provider="openai")
        except Exception as e:
            raise LLMProviderError(f"Unexpected OpenAI error: {str(e)}", provider="openai")
    
    def estimate_cost(self, messages: List[LLMMessage], model: str) -> float:
        """Estimate cost for OpenAI models."""
        total_tokens = sum(self.count_tokens(msg.content, model) for msg in messages)
        
        # OpenAI pricing (approximate)
        pricing = {
            'gpt-3.5-turbo': 0.0005,  # per 1K tokens
            'gpt-4': 0.01,
            'gpt-4-turbo-preview': 0.01
        }
        
        price_per_1k = pricing.get(model, 0.001)
        return (total_tokens / 1000) * price_per_1k
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for OpenAI models."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4


class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude LLM provider implementation."""
    
    def __init__(self, provider_config: LLMProvider):
        super().__init__(provider_config)
        if not ANTHROPIC_AVAILABLE:
            raise LLMProviderError("Anthropic library not installed")
        
        self.client = anthropic.Anthropic(api_key=provider_config.api_key)
    
    async def generate_response(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using Anthropic API."""
        self._check_rate_limit()
        
        start_time = time.time()
        
        try:
            # Convert messages to Anthropic format
            # Anthropic expects user and assistant messages, system message is separate
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    system_message = msg.content
                else:
                    user_messages.append({"role": msg.role.value, "content": msg.content})
            
            # Make API call
            response = self.client.messages.create(
                model=kwargs.get('model', self.config.models.get('fast', 'claude-3-haiku-20240307')),
                messages=user_messages,
                system=system_message if system_message else None,
                temperature=kwargs.get('temperature', 0.2),
                max_tokens=kwargs.get('max_tokens', 2048)
            )
            
            # Calculate metrics
            response_time = time.time() - start_time
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost = self.estimate_cost(messages, response.model)
            
            llm_response = LLMResponse(
                content=response.content[0].text,
                model=response.model,
                provider="anthropic",
                tokens_used=tokens_used,
                cost=cost,
                response_time=response_time
            )
            
            self.logger.log_llm_call(
                provider="anthropic",
                model=response.model,
                tokens_used=tokens_used,
                cost=cost,
                task=kwargs.get('task_name', 'unknown')
            )
            
            return llm_response
            
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(f"Anthropic authentication failed: {str(e)}", provider="anthropic")
        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {str(e)}", provider="anthropic")
        except anthropic.APIError as e:
            raise LLMProviderError(f"Anthropic API error: {str(e)}", provider="anthropic")
        except Exception as e:
            raise LLMProviderError(f"Unexpected Anthropic error: {str(e)}", provider="anthropic")
    
    def estimate_cost(self, messages: List[LLMMessage], model: str) -> float:
        """Estimate cost for Anthropic models."""
        total_tokens = sum(self.count_tokens(msg.content, model) for msg in messages)
        
        # Anthropic pricing (approximate)
        pricing = {
            'claude-3-haiku-20240307': 0.00025,  # per 1K tokens
            'claude-3-sonnet-20240229': 0.003,
            'claude-3-opus-20240229': 0.015
        }
        
        price_per_1k = pricing.get(model, 0.001)
        return (total_tokens / 1000) * price_per_1k
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for Anthropic models."""
        # Rough estimate for Anthropic models
        # Claude 3 uses a different tokenizer, but this is a reasonable approximation
        return len(text) // 4


class GoogleProvider(LLMProviderInterface):
    """Google Gemini LLM provider implementation."""
    
    def __init__(self, provider_config: LLMProvider):
        super().__init__(provider_config)
        if not GOOGLE_AVAILABLE:
            raise LLMProviderError("Google AI library not installed")
        
        genai.configure(api_key=provider_config.api_key)
    
    async def generate_response(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using Google Gemini API."""
        self._check_rate_limit()
        
        start_time = time.time()
        
        try:
            model = genai.GenerativeModel(
                kwargs.get('model', self.config.models.get('fast', 'gemini-1.5-flash'))
            )
            
            # Convert messages to Gemini format
            # Gemini uses a simple string for system prompt
            system_message = ""
            conversation_history = []
            
            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    system_message = msg.content
                else:
                    conversation_history.append(msg.content)
            
            # Combine messages for Gemini (simplified approach)
            prompt = f"{system_message}\n\n" if system_message else ""
            prompt += "\n".join(conversation_history)
            
            # Make API call
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get('temperature', 0.2),
                    max_output_tokens=kwargs.get('max_tokens', 2048)
                )
            )
            
            # Calculate metrics
            response_time = time.time() - start_time
            tokens_used = self.count_tokens(prompt + response.text, model.model_name)
            cost = self.estimate_cost(messages, model.model_name)
            
            llm_response = LLMResponse(
                content=response.text,
                model=model.model_name,
                provider="google",
                tokens_used=tokens_used,
                cost=cost,
                response_time=response_time
            )
            
            self.logger.log_llm_call(
                provider="google",
                model=model.model_name,
                tokens_used=tokens_used,
                cost=cost,
                task=kwargs.get('task_name', 'unknown')
            )
            
            return llm_response
            
        except Exception as e:
            if "API key" in str(e).lower():
                raise AuthenticationError(f"Google authentication failed: {str(e)}", provider="google")
            elif "quota" in str(e).lower():
                raise RateLimitError(f"Google rate limit exceeded: {str(e)}", provider="google")
            else:
                raise LLMProviderError(f"Google API error: {str(e)}", provider="google")
    
    def estimate_cost(self, messages: List[LLMMessage], model: str) -> float:
        """Estimate cost for Google models."""
        total_tokens = sum(self.count_tokens(msg.content, model) for msg in messages)
        
        # Google pricing (approximate)
        pricing = {
            'gemini-1.5-flash': 0.000075,  # per 1K tokens
            'gemini-1.5-pro': 0.0035
        }
        
        price_per_1k = pricing.get(model, 0.001)
        return (total_tokens / 1000) * price_per_1k
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for Google models."""
        # Rough estimate for Google models
        return len(text) // 4


class LocalProvider(LLMProviderInterface):
    """Local LLM provider implementation (e.g., Ollama)."""
    
    def __init__(self, provider_config: LLMProvider):
        super().__init__(provider_config)
        if not OPENAI_AVAILABLE:
            raise LLMProviderError("OpenAI library required for local provider compatibility")
        
        # Use OpenAI client for local endpoint compatibility
        self.client = OpenAI(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url
        )
    
    async def generate_response(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response using local LLM endpoint."""
        self._check_rate_limit()
        
        start_time = time.time()
        
        try:
            # Convert messages to OpenAI-compatible format
            openai_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]
            
            # Make API call
            response = self.client.chat.completions.create(
                model=kwargs.get('model', self.config.models.get('fast', 'llama3')),
                messages=openai_messages,
                temperature=kwargs.get('temperature', 0.2),
                max_tokens=kwargs.get('max_tokens', 2048)
            )
            
            # Calculate metrics
            response_time = time.time() - start_time
            tokens_used = response.usage.total_tokens if response.usage else 0
            cost = 0.0  # Local models are free
            
            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider="local",
                tokens_used=tokens_used,
                cost=cost,
                response_time=response_time
            )
            
            self.logger.log_llm_call(
                provider="local",
                model=response.model,
                tokens_used=tokens_used,
                cost=cost,
                task=kwargs.get('task_name', 'unknown')
            )
            
            return llm_response
            
        except Exception as e:
            raise LLMProviderError(f"Local LLM error: {str(e)}", provider="local")
    
    def estimate_cost(self, messages: List[LLMMessage], model: str) -> float:
        """Local models are free."""
        return 0.0
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for local models (rough estimate)."""
        return len(text) // 4


class LLMManager:
    """
    Central manager for LLM providers with intelligent routing.
    
    Handles provider selection, failover, cost tracking, and
    task-specific model assignment.
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("llm_manager")
        self.providers = {}
        self._initialize_providers()
        self._total_cost = 0.0
        self._total_tokens = 0
    
    def _initialize_providers(self):
        """Initialize configured LLM providers."""
        configured_providers = self.config.list_available_providers()
        
        for provider_name, provider_config in configured_providers.items():
            try:
                if provider_name == "openai":
                    self.providers[provider_name] = OpenAIProvider(provider_config)
                elif provider_name == "anthropic":
                    self.providers[provider_name] = AnthropicProvider(provider_config)
                elif provider_name == "google":
                    self.providers[provider_name] = GoogleProvider(provider_config)
                elif provider_name == "local":
                    self.providers[provider_name] = LocalProvider(provider_config)
                else:
                    # Try to use OpenAI-compatible interface for custom providers
                    self.providers[provider_name] = OpenAIProvider(provider_config)
                
                self.logger.info(f"Initialized LLM provider: {provider_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize provider {provider_name}: {str(e)}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[LLMProviderInterface]:
        """Get LLM provider by name or default."""
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]
        
        # Try to get configured default
        default_provider = self.config.get('default_provider', 'anthropic')
        if default_provider in self.providers:
            return self.providers[default_provider]
        
        # Return any available provider
        if self.providers:
            return next(iter(self.providers.values()))
        
        return None
    
    async def generate_response(
        self, 
        messages: List[Union[LLMMessage, str]], 
        task_type: str = "general",
        provider_name: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using appropriate LLM provider.
        
        Args:
            messages: List of messages or single string
            task_type: Type of task for model selection
            provider_name: Specific provider to use
            **kwargs: Additional parameters for generation
            
        Returns:
            LLMResponse with generated content and metadata
        """
        # Convert string messages to LLMMessage format
        if isinstance(messages, str):
            messages = [LLMMessage(MessageRole.USER, messages)]
        elif all(isinstance(msg, str) for msg in messages):
            messages = [
                LLMMessage(MessageRole.USER, msg) 
                for msg in messages
            ]
        
        # Get appropriate provider and model
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider:
                raise LLMProviderError(f"Provider {provider_name} not available")
            model = kwargs.get('model', self.config.get_model_for_task(task_type))
        else:
            provider_config = self.config.get_llm_provider_for_task(task_type)
            if not provider_config:
                raise LLMProviderError(f"No provider configured for task type: {task_type}")
            
            provider = self.get_provider(provider_config.name)
            model = self.config.get_model_for_task(task_type)
        
        if not provider:
            raise LLMProviderError("No LLM providers available")
        
        # Generate response
        response = await provider.generate_response(
            messages, 
            model=model or provider.config.models.get('fast'),
            task_name=task_type,
            **kwargs
        )
        
        # Update statistics
        self._total_cost += response.cost
        self._total_tokens += response.tokens_used
        
        return response
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage and cost statistics."""
        return {
            'total_cost': self._total_cost,
            'total_tokens': self._total_tokens,
            'available_providers': list(self.providers.keys()),
            'default_provider': self.config.get('default_provider')
        }
    
    def test_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Test a specific LLM provider.
        
        Returns:
            Dictionary with test results
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return {
                'provider': provider_name,
                'status': 'not_available',
                'error': 'Provider not initialized'
            }
        
        try:
            # Simple test message
            test_message = LLMMessage(MessageRole.USER, "Respond with 'Test successful'")
            response = provider.generate_response([test_message], model=provider.config.models.get('fast'))
            
            return {
                'provider': provider_name,
                'status': 'success',
                'model': response.model,
                'response_time': response.response_time,
                'tokens_used': response.tokens_used,
                'cost': response.cost
            }
            
        except Exception as e:
            return {
                'provider': provider_name,
                'status': 'error',
                'error': str(e)
            }


# Global LLM manager instance
llm_manager = LLMManager()


def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    return llm_manager