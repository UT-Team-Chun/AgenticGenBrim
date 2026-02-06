# DEV_GUIDE

## Development Commands

```bash
make fmt                # Format (Ruff)
make lint               # Lint (equivalent to CI)
make fix                # Lint + auto-fix + format
make rm-unused-imports  # Remove unused imports
make ifc                # Run the integrated CLI (run_with_repair)
```

- Ruff targets: `src tests scripts` (excluding `src/bridge_json_to_ifc`)

## Naming Conventions

- **Variables and functions**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE

## Type Annotations

- Type annotations are required for all functions
- Union types use the `X | Y` syntax (PEP 604)
- Use built-in generics (PEP 585)
- Avoid using `Any` type
  - `list[str]` OK / `List[str]` NG
  - `dict[str, int]` OK / `Dict[str, int]` NG

```python
# Good
def process(items: list[str]) -> dict[str, int] | None:
    ...

# Bad
from typing import List, Dict, Optional
def process(items: List[str]) -> Optional[Dict[str, int]]:
    ...
```

## Pydantic

- Do not use `dict` / `tuple` as return types; define types using Pydantic models instead
- Manage hardcoded strings with `StrEnum` or Pydantic models
- Avoid using `.value` as much as possible (use `StrEnum` directly)

```python
# Good
class GoverningCheck(StrEnum):
    DECK = "deck"
    BEND = "bend"

def get_check() -> GoverningCheck:
    return GoverningCheck.DECK

# Bad
def get_check() -> str:
    return "deck"
```

## Logging

```python
from src.bridge_agentic_generate.logger_config import logger

logger.info("Processing started")
logger.debug(f"Parameters: {params}")
logger.error(f"Error occurred: {e}")
```

- `print` is prohibited

## CLI

- Always use `fire` for CLI argument management

```python
import fire

class CLI:
    def run(self, bridge_length_m: float = 50.0) -> None:
        ...

if __name__ == "__main__":
    fire.Fire(CLI)
```

## File Operations

- Use `pathlib.Path` for file and directory operations

```python
from pathlib import Path

output_dir = Path("data/generated_ifc")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "sample.ifc"
```

## Docstring

- Google-style Docstrings (in Japanese)

```python
def calculate_util(stress: float, allowable: float) -> float:
    """応力度比を計算する。

    Args:
        stress: 発生応力度 [N/mm²]
        allowable: 許容応力度 [N/mm²]

    Returns:
        応力度比（util）
    """
    return stress / allowable
```

## Prohibited Practices

- Swallowing exceptions with `try: ... except: pass` is prohibited
- Remove unused code and commented-out code
- Do not leave backward-compatibility remnants (unused `_vars`, re-exports, `// removed` comments, etc.)
- Avoid magic numbers; define them as constants before use
- One responsibility per function — keep functions focused and composable

```python
# Bad
if thickness < 160:
    ...

# Good
MIN_DECK_THICKNESS_MM = 160
if thickness < MIN_DECK_THICKNESS_MM:
    ...
```

## Testing

- Use mocks for tests that involve LLM processing
- Place test files in the `tests/` directory

## Git

- Do not automatically run `git add/commit` (only suggest commit messages)
- Do not commit `.env` files
- `data/` and `rag_index/` are included in `.gitignore`
