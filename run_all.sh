#!/usr/bin/env bash
# Rebuild everything from data/raw, in order.
set -e
python src/ira_data/extract_quarterly_general.py
python src/ira_data/extract_statements.py
python src/ira_data/build_panel.py
python src/ira_data/quality_flags.py
python src/ira_data/build_class_panel.py
python src/ira_data/validate.py
python src/ira_data/build_explorer_data.py
