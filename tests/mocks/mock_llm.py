"""
Mock LLM Provider for testing.

Provides a fake LLM that returns predictable responses without
making actual API calls.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, UTC


class MockLLMResponse:
    """Mock response object that mimics actual LLM responses."""
    
    def __init__(self, content: str, tokens_used: int = 100, cost: float = 0.001):
        self.content = content
        self.tokens_used = tokens_used
        self.cost = cost
        self.response_time = 0.1
        self.model = "mock-model"
        self.provider = "mock"
        self.timestamp = datetime.now(UTC)
        self.metadata = {}


class MockLLMProvider:
    """
    Mock LLM provider for testing.
    
    Can be configured to return specific responses or simulate failures.
    """
    
    def __init__(self, name: str = "mock"):
        self.name = name
        self.call_count = 0
        self.calls_history = []
        self.should_fail = False
        self.failure_message = "Mock LLM failure"
        self.response_template = "Mock LLM response for: {prompt}"
        self.custom_responses = {}
        
    async def generate_response(
        self, 
        messages: List,
        task_name: str = "unknown",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> MockLLMResponse:
        """Generate a mock response."""
        self.call_count += 1
        
        # Extract prompt from messages
        prompt = ""
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                prompt = last_message.content
            elif isinstance(last_message, dict):
                prompt = last_message.get('content', '')
        
        # Record call
        self.calls_history.append({
            'prompt': prompt,
            'task_name': task_name,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'kwargs': kwargs
        })
        
        # Simulate failure if configured
        if self.should_fail:
            raise Exception(self.failure_message)
        
        # Check for custom response
        if task_name in self.custom_responses:
            content = self.custom_responses[task_name]
        else:
            content = self.response_template.format(prompt=prompt[:50])
        
        return MockLLMResponse(
            content=content,
            tokens_used=len(content.split()),
            cost=0.001
        )
    
    def set_response_for_task(self, task_name: str, response: str):
        """Configure a specific response for a task."""
        self.custom_responses[task_name] = response
    
    def configure_failure(self, should_fail: bool = True, message: str = None):
        """Configure the provider to simulate failures."""
        self.should_fail = should_fail
        if message:
            self.failure_message = message
    
    def reset(self):
        """Reset call history and configuration."""
        self.call_count = 0
        self.calls_history = []
        self.should_fail = False
        self.custom_responses = {}
    
    def get_call_count(self) -> int:
        """Get number of times generate_response was called."""
        return self.call_count
    
    def get_last_prompt(self) -> Optional[str]:
        """Get the last prompt sent to the provider."""
        if self.calls_history:
            return self.calls_history[-1]['prompt']
        return None


class MockLLMManager:
    """
    Mock LLM manager for testing.
    
    Replaces the real LLM manager in tests.
    """
    
    def __init__(self):
        self.providers = {
            'fast': MockLLMProvider('mock-fast'),
            'quality': MockLLMProvider('mock-quality')
        }
        self.default_provider = 'fast'
        self.total_cost = 0.0
        self.total_tokens = 0
    
    def get_provider(self, tier: str = None):
        """Get a mock provider by tier."""
        tier = tier or self.default_provider
        return self.providers.get(tier, self.providers['fast'])
    
    async def generate_response(self, messages: List, task_name: str = "unknown", tier: str = None, **kwargs):
        """Generate a response using the appropriate tier."""
        provider = self.get_provider(tier)
        response = await provider.generate_response(messages, task_name, **kwargs)
        
        self.total_cost += response.cost
        self.total_tokens += response.tokens_used
        
        return response
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get mock usage statistics."""
        return {
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'available_providers': list(self.providers.keys()),
            'calls_by_provider': {
                name: provider.call_count 
                for name, provider in self.providers.items()
            }
        }
    
    def reset_all(self):
        """Reset all providers."""
        for provider in self.providers.values():
            provider.reset()
        self.total_cost = 0.0
        self.total_tokens = 0
