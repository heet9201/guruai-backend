"""
Response helper utilities for API endpoints.
"""
from flask import jsonify
from typing import Any, Dict, Optional

def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> tuple:
    """Create a standardized success response."""
    response_data = {
        "success": True,
        "message": message,
        "data": data
    }
    return jsonify(response_data), status_code

def error_response(message: str = "Error", error: Optional[str] = None, status_code: int = 400) -> tuple:
    """Create a standardized error response."""
    response_data = {
        "success": False,
        "message": message
    }
    
    if error:
        response_data["error"] = error
    
    return jsonify(response_data), status_code

def paginated_response(data: Any, page: int, limit: int, total: int, message: str = "Success") -> tuple:
    """Create a standardized paginated response."""
    response_data = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": (page * limit) < total,
            "has_prev": page > 1
        }
    }
    return jsonify(response_data), 200
