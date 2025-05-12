"""
Utility functions for services
"""
from typing import Dict, Any

def filter_user_data(user_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out sensitive information from user data
    
    Args:
        user_dict: Dictionary containing user data
        
    Returns:
        Dictionary with only safe user information
    """
    safe_fields = [
        "user_id", 
        "username", 
        "created_at", 
        "updated_at", 
        "deleted_at"
    ]
    
    return {k: v for k, v in user_dict.items() if k in safe_fields} 