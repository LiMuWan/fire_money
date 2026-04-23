"""Strategy script plugin namespace.

Runtime loader scans this directory for `*.py` files that do not start with `_`.
Each plugin script should expose:

- `STRATEGY_DEFINITION`: dict
- optional `compute_score(context, *, dependency_scores, definition)`
"""

