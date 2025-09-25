"""
Base classes for blocking policies.

This module defines the core interfaces and base classes for blocking policies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import time
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union, Any, Type, TypeVar, Generic

from focus_guard.core.domain.models import Domain, Category


class BlockingPolicyType(str, Enum):
    """Types of blocking policies."""
    TIME_BASED = "time_based"
    DOMAIN = "domain"
    APPLICATION = "application"
    CONTENT = "content"
    CUSTOM = "custom"


@dataclass
class BlockingPolicyConfig:
    """Configuration for a blocking policy."""
    policy_type: BlockingPolicyType
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


T = TypeVar('T', bound='BlockingPolicy')


class BlockingPolicy(ABC):
    """
    Base class for all blocking policies.
    
    A blocking policy defines rules for when and how to block access to resources.
    """
    
    def __init__(self, config: BlockingPolicyConfig):
        """Initialize the blocking policy with the given configuration."""
        self.config = config
        self._enabled = config.enabled
    
    @property
    def name(self) -> str:
        """Get the name of the policy."""
        return self.config.name
    
    @property
    def policy_type(self) -> BlockingPolicyType:
        """Get the type of the policy."""
        return self.config.policy_type
    
    @property
    def is_enabled(self) -> bool:
        """Check if the policy is enabled."""
        return self._enabled
    
    def enable(self) -> None:
        """Enable the policy."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable the policy."""
        self._enabled = False
    
    @abstractmethod
    def should_block(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if the given resource should be blocked.
        
        Args:
            resource: The resource to check (domain, application name, etc.)
            context: Additional context for the decision
            
        Returns:
            bool: True if the resource should be blocked, False otherwise
        """
        pass
    
    @abstractmethod
    def get_block_reason(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the reason why a resource would be blocked.
        
        Args:
            resource: The resource to check
            context: Additional context for the decision
            
        Returns:
            str: A human-readable reason for blocking
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy to a dictionary."""
        return {
            "type": self.policy_type.value,
            "name": self.name,
            "enabled": self.is_enabled,
            "description": self.config.description,
            "priority": self.config.priority,
            "metadata": self.config.metadata,
        }
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create a policy from a dictionary."""
        policy_type = BlockingPolicyType(data["type"])
        config = BlockingPolicyConfig(
            policy_type=policy_type,
            name=data["name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {})
        )
        return cls(config)
