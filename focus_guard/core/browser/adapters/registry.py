"""
Adapter registry implementation.

This module handles the registration and retrieval of adapter implementations.
"""

from typing import Type, TypeVar, Dict, Any

# Type variable for adapter interfaces
T = TypeVar('T')

# Registry for adapter implementations
_ADAPTER_REGISTRY: Dict[Type, Type] = {}

def register_adapter(interface: Type[T], implementation: Type[T]) -> None:
    """Register an adapter implementation for an interface.
    
    Args:
        interface: The interface class
        implementation: The implementation class
    """
    _ADAPTER_REGISTRY[interface] = implementation

def get_adapter(interface: Type[T], *args, **kwargs) -> T:
    """Get an adapter instance for the specified interface.
    
    Args:
        interface: The interface class to get an adapter for
        *args: Positional arguments to pass to the adapter constructor
        **kwargs: Keyword arguments to pass to the adapter constructor
        
    Returns:
        An instance of the adapter implementing the interface
        
    Raises:
        ValueError: If no adapter is registered for the interface
    """
    if interface not in _ADAPTER_REGISTRY:
        raise ValueError(f"No adapter registered for interface: {interface.__name__}")
    return _ADAPTER_REGISTRY[interface](*args, **kwargs)
