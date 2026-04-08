from __future__ import annotations

from typing import Any


class ShopDemoMutator:
    def mutate_value(self, value: Any, kind: str, seeds: list[str]) -> list[str]:
        text = "" if value is None else str(value)
        variants: list[str] = []

        def add(candidate: Any) -> None:
            rendered = "" if candidate is None else str(candidate)
            if rendered != text and rendered not in variants:
                variants.append(rendered)

        for seed in seeds:
            add(seed)

        if kind in {"text", "textarea"}:
            add("")
            add(text + "_mut")
            add(text + "'\"<>")
            add("A" * 64)
        elif kind in {"price", "stock", "quantity", "identifier"}:
            try:
                number = int(float(text))
            except ValueError:
                number = 0
            add(number - 1)
            add(number + 1)
            add(0)
            add(9999)
            if kind == "identifier":
                add(-1)
        elif kind == "scenario":
            add("single")
            add("full")
            add("chaos")
        else:
            add(text + "_alt")

        return variants[:4]
