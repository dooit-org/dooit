from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
from typing import Callable, List, Optional, Tuple, Union

from ._base import ApiComponent
from dooit.ui.api.events import ModeType

KeyBindType = defaultdict[str, defaultdict[str, Optional["DooitFunction"]]]
KeyType = Union[str, List[str]]


@dataclass
class DooitFunction:
    """
    Represents a callable function bound to a key in Dooit,
    along with its description and grouping metadata.
    """

    callback: Callable
    description: str = ""
    group: str = ""

    def __post_init__(self):
        self.description = self.description.strip("\n")


class KeyMatchType(Enum):
    """
    Enumeration of possible outcomes when matching a key sequence
    against registered keybindings.
    """

    NoMatchFound = "NoMatchFound"
    MultipleMatchFound = "MultipleMatchFound"
    MatchFound = "MatchFound"


@dataclass
class KeyMatch:
    """
    Represents the result of attempting to match a key sequence
    against registered keybindings, containing the match type
    and optionally the matched function.
    """

    match_type: KeyMatchType
    function: Optional[DooitFunction] = None

    @staticmethod
    def no_match():
        """Create a KeyMatch indicating no matching keybinding was found."""
        return KeyMatch(match_type=KeyMatchType.NoMatchFound)

    @staticmethod
    def multiple_match():
        """Create a KeyMatch indicating multiple potential matches exist."""
        return KeyMatch(match_type=KeyMatchType.MultipleMatchFound)

    @staticmethod
    def match_found(func: DooitFunction):
        """Create a KeyMatch indicating an exact match was found for the given function."""
        return KeyMatch(match_type=KeyMatchType.MatchFound, function=func)


class KeyManager(ApiComponent):
    """
    Manages keybinding registration and key sequence matching for the Dooit application.
    Tracks user key inputs and resolves them against registered keybindings.
    """

    def __init__(self, get_mode: Callable) -> None:
        self.keybinds: KeyBindType = defaultdict(lambda: defaultdict(lambda: None))
        self._inputs: List[str] = []
        self.get_mode = get_mode

    @property
    def groups(self) -> List[str]:
        """Return a sorted list of unique keybinding group names in NORMAL mode."""
        return list(
            sorted(set(func.group for func in self.keybinds["NORMAL"].values() if func))
        )

    def get_keybinds_by_group(self, group: str) -> List[Tuple[str, DooitFunction]]:
        """Return all keybindings in NORMAL mode that belong to the specified group."""
        return [
            (key, func)
            for key, func in self.keybinds["NORMAL"].items()
            if func and func.group == group
        ]

    def __set_key(
        self,
        mode: ModeType,
        key: str,
        callback: Callable,
        description: Optional[str],
        group: str,
    ) -> None:
        self.keybinds[mode][key] = DooitFunction(
            callback, description or callback.__doc__ or "", group
        )

    def set(
        self,
        keys: KeyType,
        callback: Callable,
        description: Optional[str] = None,
        group: str = "",
    ) -> None:
        """Register a callback for one or more keys in NORMAL mode."""
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            self.__set_key("NORMAL", key, callback, description, group)

    @property
    def input(self) -> str:
        """Return the current accumulated key input as a formatted string."""
        formatted = ""
        for i in self._inputs:
            if len(i) > 1:
                formatted += f"<{i}>"
            else:
                formatted += i

        return formatted

    def clear_input(self):
        """Clear all accumulated key inputs."""
        self._inputs.clear()

    def _find_matched_functions(self) -> List[DooitFunction]:
        keybinds = self.keybinds[self.get_mode()].items()
        return [func for key, func in keybinds if key.startswith(self.input) and func]

    def search_for_key(self) -> KeyMatch:
        """Search for a keybinding match based on the current accumulated input."""
        matched = self._find_matched_functions()
        if not matched:
            self.clear_input()
            return KeyMatch.no_match()

        if len(matched) > 1 or self.input not in self.keybinds[self.get_mode()]:
            return KeyMatch.multiple_match()

        self.clear_input()
        return KeyMatch.match_found(matched[0])

    def register_key(self, key: str) -> KeyMatch:
        """Register a key press and return the resulting match status."""
        if key == "escape":
            self.clear_input()
            return KeyMatch.no_match()

        self._inputs.append(key)
        return self.search_for_key()
