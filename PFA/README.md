# Personal Finance Agent
Learning exercise. Build only what this file lists. If a request adds anything else, say it is out of scope and do not write it.
## What to build
An agent that answers questions about a person's transactions by calling tools.
Example question: "How much did I spend on food last month?"
The model must not calculate the answer from memory. It must call tools, then answer from the tool results.
## Tools
Use these four tools only.
| Tool | Arguments | Returns |
| --- | --- | --- |
| `get_transactions` | none | every transaction |
| `filter_transactions` | `category` (string, optional), `start_date` (YYYY-MM-DD, optional), `end_date` (YYYY-MM-DD, optional) | matching transactions |
| `calculate_total` | `transaction_ids` (list of integers) | sum of those amounts |
| `get_categories` | none | list of category names |
Each transaction has: `id`, `date`, `amount`, `category`, `description`.
A spending question must use more than one tool. Expected path for the example question:
1. `filter_transactions` for category and dates
2. `calculate_total` with the ids from that result
3. a short final answer that uses the total
`get_transactions` and `get_categories` stay available so the model can list data or look up a category name.
