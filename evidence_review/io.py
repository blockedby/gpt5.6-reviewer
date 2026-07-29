"""JSON and file I/O helpers."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, TextIO


class InputError(Exception):
    """An input could not be read or decoded."""


def read_text(path_value: str, *, stdin: TextIO | None = None) -> str:
    """Read UTF-8 text from a path, or from stdin when the path is ``-``."""
    if path_value == "-":
        stream = stdin if stdin is not None else sys.stdin
        try:
            return stream.read()
        except OSError as exc:
            raise InputError(f"cannot read stdin: {exc}") from exc

    path = Path(path_value)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc


def read_json(path_value: str, *, stdin: TextIO | None = None) -> Any:
    """Read strict JSON from a path or stdin.

    Duplicate object keys and JavaScript constants such as ``NaN`` are
    rejected instead of being silently normalized by :mod:`json`.
    """
    text = read_text(path_value, stdin=stdin)
    source = "stdin" if path_value == "-" else path_value

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate object key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-standard numeric constant {value}")

    try:
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise InputError(
            f"cannot parse JSON from {source}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise InputError(f"cannot parse JSON from {source}: {exc}") from exc


def encode_json(value: Any) -> str:
    """Encode deterministic, human-readable JSON."""
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_text(
    text: str,
    path_value: str | None,
    *,
    stdout: TextIO | None = None,
) -> None:
    """Write to stdout, or atomically replace an explicit UTF-8 output file."""
    if path_value in {None, "-"}:
        stream = stdout if stdout is not None else sys.stdout
        try:
            stream.write(text)
            stream.flush()
        except OSError as exc:
            raise InputError(f"cannot write stdout: {exc}") from exc
        return

    path = Path(path_value)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except OSError as exc:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass
        raise InputError(f"cannot write {path}: {exc}") from exc


def write_json(
    value: Any,
    path_value: str | None,
    *,
    stdout: TextIO | None = None,
) -> None:
    """Encode JSON and write it to stdout or an explicit output file."""
    write_text(encode_json(value), path_value, stdout=stdout)
