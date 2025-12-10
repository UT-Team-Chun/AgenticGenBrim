PYTHON := uv run python
RUFF := uv run ruff

.PHONY: fmt fix lint

# コード整形だけ
fmt:
	$(RUFF) format src

# Lint + 自動修正（import 並び替え含む）+ フォーマット
fix:
	$(RUFF) check src --fix --ignore F401
	$(RUFF) format src

# Lint だけ（CI 相当）
lint:
	$(RUFF) check src
