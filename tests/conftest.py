# Copyright 2026 OpenAI
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

import importlib
from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest


CANDIDATE_MODULES = ("allocator", "patchwork.allocator", "src.allocator")
CANDIDATE_CALLABLES = ("allocate", "run", "run_allocator", "allocate_sessions")


def _load_allocator_callable() -> Callable[[dict[str, Any]], dict[str, Any]] | None:
    for module_name in CANDIDATE_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue

        for fn_name in CANDIDATE_CALLABLES:
            fn = getattr(module, fn_name, None)
            if callable(fn):
                return fn
    return None


@pytest.fixture(scope="session")
def allocator_fn() -> Callable[[dict[str, Any]], dict[str, Any]]:
    fn = _load_allocator_callable()
    if fn is None:
        pytest.skip(
            "allocator callable was not found. Expected one of: "
            f"{CANDIDATE_MODULES} with function {CANDIDATE_CALLABLES}."
        )
    return fn


def allocate_twice(
    allocator_fn: Callable[[dict[str, Any]], dict[str, Any]], scenario: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = allocator_fn(deepcopy(scenario))
    second = allocator_fn(deepcopy(scenario))
    return first, second


def iter_items(obj: Any, item_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in item_keys:
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def collect_values(obj: Any, target_key: str) -> list[Any]:
    values: list[Any] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == target_key:
                    values.append(v)
                _walk(v)
        elif isinstance(node, list):
            for i in node:
                _walk(i)

    _walk(obj)
    return values
