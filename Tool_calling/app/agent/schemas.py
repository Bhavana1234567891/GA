"""
Tool schemas — the contracts the LLM (or rules planner) must follow.

A schema tells the model:
  - the tool name
  - what the tool does (description)
  - which arguments exist, their types, and which are required

This is the "function calling" interface. The model never sees the Python
source of the tools; it only sees these JSON Schema objects.
"""

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_transactions",
            "description": (
                "Fetch the most recent transactions, newest first. "
                "Use this for questions like 'show my latest purchases' "
                "when no category, merchant, or date filter is needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many rows to return (1-100). Default 20.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of rows to skip for pagination. Default 0.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_transactions",
            "description": (
                "Search transactions by category, merchant, date range, and amount. "
                "Use this to list matching purchases, not to compute a sum."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category name or fragment, e.g. 'Food' or 'Food & Dining'.",
                    },
                    "merchant": {
                        "type": "string",
                        "description": "Merchant name or fragment, e.g. 'Starbucks'.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Inclusive start date as YYYY-MM-DD.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Inclusive end date as YYYY-MM-DD.",
                    },
                    "min_amount": {"type": "number"},
                    "max_amount": {"type": "number"},
                    "sort_by": {
                        "type": "string",
                        "enum": ["date", "amount"],
                        "description": "Default 'date'. Use 'amount' for largest/smallest questions.",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                    },
                    "limit": {"type": "integer", "description": "Max rows to return (1-100)."},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_total",
            "description": (
                "Sum spending for optional category, merchant, and date filters. "
                "Always use this for 'how much did I spend' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "merchant": {"type": "string"},
                    "start_date": {
                        "type": "string",
                        "description": "Inclusive start date as YYYY-MM-DD.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Inclusive end date as YYYY-MM-DD.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_categories",
            "description": (
                "List every spending category with transaction counts and totals. "
                "Call this first when the user says a casual name like 'food' or "
                "'subscriptions' so you can map it to the real category name."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]
