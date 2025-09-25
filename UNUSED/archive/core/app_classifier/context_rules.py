"""
Defines rules for which app categories are allowed in different contexts.
"""
from typing import Dict, List, Set, Optional

class ContextRules:
    """
    Defines rules for application usage in different contexts.
    Each context can have allowed, blocked, and flagged app categories.
    """
    
    def __init__(self):
        self.rules: Dict[str, Dict[str, Set[str]]] = {
            # Default rules apply when no specific context is detected
            "default": {
                "allowed": {"productivity", "programming", "documentation", "browser"},
                "blocked": {"gaming", "entertainment"},
                "flag": {"social_media"}
            },
            # Meeting context
            "meeting": {
                "allowed": {"communication", "browser", "documentation"},
                "blocked": {"gaming", "entertainment"},
                "flag": {"social_media"}
            },
            # Focus work
            "focus_work": {
                "allowed": {"productivity", "programming", "documentation"},
                "blocked": {"gaming", "entertainment", "social_media"},
                "flag": {"browser"}
            },
            # Math/Science work
            "math_science": {
                "allowed": {"math_science", "documentation", "browser"},
                "blocked": {"gaming", "entertainment", "social_media"},
                "flag": set()
            },
            # Break time
            "break": {
                "allowed": {"entertainment", "browser", "social_media"},
                "blocked": set(),
                "flag": set()
            },
            # After hours
            "after_hours": {
                "allowed": {"entertainment", "browser", "social_media"},
                "blocked": {"work", "productivity"},
                "flag": set()
            }
        }
    
    def get_rules(self, context: str) -> Dict[str, Set[str]]:
        """Get rules for a specific context, falling back to default if not found."""
        return self.rules.get(context.lower(), self.rules["default"])
    
    def is_allowed(self, category: str, context: str) -> Dict[str, bool]:
        """
        Check if an app category is allowed in the given context.
        
        Returns:
            Dict with 'allowed' (bool) and 'reason' (str) keys
        """
        if not category or category == "unknown":
            return {"allowed": True, "reason": "Unknown category - allowing by default"}
            
        rules = self.get_rules(context)
        
        # Check blocked categories first
        if category in rules.get("blocked", set()):
            return {
                "allowed": False,
                "reason": f"Category '{category}' is blocked in '{context}' context"
            }
            
        # Check if category needs to be in allowed list
        allowed_categories = rules.get("allowed", set())
        if allowed_categories and category not in allowed_categories:
            return {
                "allowed": False,
                "reason": f"Category '{category}' not in allowed categories for '{context}'"
            }
            
        # Check if category should be flagged
        if category in rules.get("flag", set()):
            return {
                "allowed": True,
                "reason": f"Category '{category}' is flagged in '{context}' context"
            }
            
        return {"allowed": True, "reason": "Allowed by rules"}
    
    def get_allowed_categories(self, context: str) -> Set[str]:
        """Get all allowed categories for a context."""
        rules = self.get_rules(context)
        return rules.get("allowed", set())
    
    def get_blocked_categories(self, context: str) -> Set[str]:
        """Get all blocked categories for a context."""
        rules = self.get_rules(context)
        return rules.get("blocked", set())
    
    def get_flagged_categories(self, context: str) -> Set[str]:
        """Get all flagged categories for a context."""
        rules = self.get_rules(context)
        return rules.get("flag", set())
