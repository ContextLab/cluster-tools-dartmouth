from typing import Any, Callable, Dict, Iterable, List, NoReturn, Optional

from clustertools.shared.environ import PseudoEnviron


class MonitoredEnviron(PseudoEnviron):
    # ADD DOCSTRING

    @staticmethod
    def _default_update_hook():
        pass

    def __init__(
            self,
            initial_env: Dict[str, str],
            custom_vars: Dict[str, str],
            update_hook: Optional[Callable[[], None]] = None,
    ) -> None:
        # ADD DOCSTRING
        super().__init__(initial_env=initial_env, custom_vars=custom_vars)
        if update_hook is None:
            self.update_hook = MonitoredEnviron._default_update_hook
        else:
            self.update_hook = update_hook

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key=key)
        self.update_hook()

    def __setitem__(self, key: str, value: str) -> None:
        super().__setitem__(key=key, value=value)
        self.update_hook()

    # noinspection PyPep8Naming
    def update(self, E, **F) -> None:
        super().update(E, **F)
        self.update_hook()


class MonitoredList(list):
    # ADD DOCSTRING

    @staticmethod
    def _default_update_hook():
        pass

    def __init__(self, list_: List[Any], update_hook: Optional[Callable[..., None]] = None):
        super().__init__(list_)
        self._update_hook = update_hook

    def __add__(self, other: List[Any]) -> List[Any]:
        result = super().__add__(other)
        self._update_hook()
        return result

    def __delitem__(self, key: int) -> None:
        super().__delitem__(key)
        self._update_hook()

    def __iadd__(self, other: List[Any]):
        super().__iadd__(other)
        self._update_hook()

    def __imul__(self, other: int) -> NoReturn:
        raise TypeError(
            f"unsupported operand type(s) for *=: '{self.__class__.__name__}' "
            f" and '{other.__class__.__name__}'"
        )

    def __mul__(self, other: int) -> NoReturn:
        raise TypeError(
            f"unsupported operand type(s) for *: '{self.__class__.__name__}' "
            f" and '{other.__class__.__name__}'"
        )

    def __rmul__(self, other: int) -> NoReturn:
        raise TypeError(
            f"unsupported operand type(s) for *: '{other.__class__.__name__}' "
            f" and '{self.__class__.__name__}'"
        )

    def __setitem__(self, key: int, value: Any) -> None:
        super().__setitem__(key, value)
        self._update_hook()

    def append(self, obj: Any) -> None:
        super().append(obj)
        self._update_hook()

    def clear(self) -> None:
        super().clear()
        self._update_hook()

    def extend(self, iterable: Iterable[Any]) -> None:
        super().extend(iterable)
        self._update_hook()

    def insert(self, index: int, obj: Any) -> None:
        super().insert(index, obj)
        print('insert called')

    def pop(self, index: int = -1) -> Any:
        super().pop(index)
        self._update_hook()

    def remove(self, value: Any) -> None:
        super().remove(value)
        self._update_hook()
