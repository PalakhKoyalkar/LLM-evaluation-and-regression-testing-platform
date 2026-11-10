import re
from typing import Any

_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, variables: dict[str, Any]) -> str:
    def substitute(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"template variable '{key}' missing from test case input")
        return str(variables[key])

    return _VAR.sub(substitute, template)
