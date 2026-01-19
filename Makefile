PYTHON := uv run python
RUFF := uv run ruff
TARGETS := src tests scripts
EXCLUDE := --exclude src/bridge_json_to_ifc

.PHONY: fmt fix lint rm-unused-imports

# コード整形だけ
fmt:
	$(RUFF) format $(TARGETS) $(EXCLUDE)

# Lint + 自動修正（import 並び替え含む）+ フォーマット
fix:
	$(RUFF) check $(TARGETS) --fix --ignore F401 $(EXCLUDE)
	$(RUFF) format $(TARGETS) $(EXCLUDE)

# Lint だけ（CI 相当）
lint:
	$(RUFF) check $(TARGETS) $(EXCLUDE)

# 未使用インポートを削除
rm-unused-imports:
	$(RUFF) check $(TARGETS) --fix --select=F401 $(EXCLUDE)
