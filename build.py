#!/usr/bin/env python3
"""Собирает index.html из PRIVACY.md.

Запуск: python3 build.py
Требуется модуль python3-markdown (в Debian/Ubuntu: python3-markdown).
"""
import pathlib
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit("Не найден модуль markdown. Установите: sudo apt install python3-markdown")

root = pathlib.Path(__file__).resolve().parent
src = (root / "PRIVACY.md").read_text(encoding="utf-8")

# Python-Markdown требует пустую строку перед списком. В PRIVACY.md она есть не везде,
# поэтому нормализуем перед конвертацией: вставляем пустую строку перед первым
# элементом списка, который идёт сразу после обычного абзаца.
normalized = []
for line in src.splitlines():
    is_item = re.match(r"^\s*[-*]\s+", line) is not None
    prev_is_item = bool(normalized) and re.match(r"^\s*[-*]\s+", normalized[-1]) is not None
    if is_item and normalized and normalized[-1].strip() and not prev_is_item:
        normalized.append("")
    normalized.append(line)
body = markdown.markdown("\n".join(normalized) + "\n", extensions=["extra", "sane_lists"])

template = (root / "template.html").read_text(encoding="utf-8")
(root / "index.html").write_text(template.replace("<!--BODY-->", body), encoding="utf-8")
print("index.html:", (root / "index.html").stat().st_size, "байт")
