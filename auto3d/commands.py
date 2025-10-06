"""Subcommand registry for the Auto3D application wrapper."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Dict, Iterable

from .app import Auto3DApplication


@dataclass
class Command:
    """Representation of a CLI subcommand."""

    name: str
    help: str
    configure: Callable[[argparse.ArgumentParser], None]
    handler: Callable[[Auto3DApplication, argparse.Namespace], None]


class CommandRegistry:
    """A thin registry that owns Auto3D command definitions."""

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}

    def register(self, command: Command) -> None:
        if command.name in self._commands:
            msg = f"Command '{command.name}' already registered"
            raise ValueError(msg)
        self._commands[command.name] = command

    def __contains__(self, name: str) -> bool:  # pragma: no cover - trivial
        return name in self._commands

    def __getitem__(self, name: str) -> Command:
        return self._commands[name]

    def values(self) -> Iterable[Command]:  # pragma: no cover - trivial
        return self._commands.values()


command_registry = CommandRegistry()
