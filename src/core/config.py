"""
Configuration management for the literature review system.

Handles loading and validation of YAML configuration files,
environment variable substitution, and LLM provider settings.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class LLMProvider:
    """Configuration for an LLM provider."""
    name: str
    api_key: str
    base_url: str
    models: Dict[str, str]
    pricing: Dict[str, float]
    rate_limits: Dict[str, int]


@dataclass
class RateLimit:
    """Rate limiting configuration."""
    requests_per_minute: int
    tokens_per_minute: int


class ConfigManager:
    """
    Central configuration manager for the literature review system.
    
    Loads configuration from YAML files, handles environment variable
    substitution, and provides access to all system settings.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config = {}
        self._llm_providers = {}
        self._load_config()
    
    def _load_config(self):
        """Load all configuration files."""
        # Load main configuration
        main_config_path = self.config_dir / "config.yaml"
        if main_config_path.exists():
            with open(main_config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        
        # Load LLM provider configuration
        llm_config_path = self.config_dir / "llm_providers.yaml"
        if llm_config_path.exists():
            with open(llm_config_path, 'r') as f:
                llm_config = yaml.safe_load(f)
                self._load_llm_providers(llm_config)
    
    def _substitute_env_vars(self, text: str) -> str:
        """Replace ${VAR} patterns with environment variables."""
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        
        return re.sub(pattern, replace_var, text)
    
    def _load_llm_providers(self, llm_config: Dict[str, Any]):
        """Load LLM provider configurations."""
        providers_config = llm_config.get('providers', {})
        rate_limits_config = llm_config.get('rate_limits', {})
        
        for provider_name, config in providers_config.items():
            # Substitute environment variables
            api_key = self._substitute_env_vars(config.get('api_key', ''))
            base_url = config.get('base_url', '')
            
            # Get rate limits
            rate_limits = rate_limits_config.get(provider_name, {
                'requests_per_minute': 60,
                'tokens_per_minute': 90000
            })
            
            self._llm_providers[provider_name] = LLMProvider(
                name=provider_name,
                api_key=api_key,
                base_url=base_url,
                models=config.get('models', {}),
                pricing=config.get('pricing', {}),
                rate_limits=rate_limits
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'search.year_min')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_llm_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get LLM provider configuration."""
        return self._llm_providers.get(provider_name)
    
    def get_llm_provider_for_task(self, task_type: str) -> Optional[LLMProvider]:
        """
        Get the appropriate LLM provider for a specific task.
        
        Args:
            task_type: Type of task (e.g., 'query_formulation', 'summarization')
            
        Returns:
            LLMProvider instance or None
        """
        # Get the quality tier for this task
        tier = self.get(f'llm_assignments.{task_type}', 'fast')
        
        # Get the default provider
        default_provider = self.get('llm_assignments.default_provider', 'anthropic')
        
        # Try to get the configured provider
        provider = self.get_llm_provider(default_provider)
        if provider and tier in provider.models:
            return provider
        
        # Fallback to any available provider with the required tier
        for provider in self._llm_providers.values():
            if tier in provider.models:
                return provider
        
        return None
    
    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get the appropriate model for a specific task.
        
        Args:
            task_type: Type of task (e.g., 'query_formulation', 'summarization')
            
        Returns:
            Model name string or None
        """
        tier = self.get(f'llm_assignments.{task_type}', 'fast')
        provider = self.get_llm_provider_for_task(task_type)
        
        if provider and tier in provider.models:
            return provider.models[tier]
        
        return None
    
    def list_available_providers(self) -> Dict[str, LLMProvider]:
        """List all configured LLM providers."""
        return self._llm_providers.copy()
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate the configuration and return status.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check required configuration sections
        required_sections = ['project', 'search', 'quality_filters', 'llm_assignments']
        for section in required_sections:
            if section not in self._config:
                issues.append(f"Missing required configuration section: {section}")
        
        # Check LLM provider configurations
        if not self._llm_providers:
            issues.append("No LLM providers configured")
        
        for provider_name, provider in self._llm_providers.items():
            if not provider.api_key and provider_name != 'local':
                warnings.append(f"Provider {provider_name} has no API key configured")
            
            if not provider.models:
                issues.append(f"Provider {provider_name} has no models configured")
        
        # Check output directory
        output_dir = self.get('project.output_dir', './data/output')
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            issues.append(f"Cannot create output directory {output_dir}: {e}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }


# Global configuration instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration instance."""
    return config


def reload_config():
    """Reload configuration from files."""
    global config
    config = ConfigManager()
    return config