from typing import Any, Callable, Dict, Iterable, List, NoReturn, Optional

from clustertools.shared.environ import PseudoEnviron


class MonitoredEnviron(PseudoEnviron):
    # ADD DOCSTRING

    @staticmethod
    def _default_hook(*args, **kwargs):
        pass

    def __init__(
            self,
            initial_env: Dict[str, str],
            custom_vars: Dict[str, str],
            validate_item_hook: Optional[Callable[[Dict[str, str]], None]] = None,
            post_update_hook: Optional[Callable[[], None]] = None,
    ) -> None:
        # ADD DOCSTRING
        #  validate_item_hook is run before creating or editing
        #  key/value pairs. Can be used to enforce certain properties of
        #  keys/values, prevent editing of or constrain values for
        #  certain keys, etc. Receives a dict of keys/value pairs to be
        #  added/updated. Not run before removing keys.
        #  NOTE: validate_item_hook need not enforce the main constraint
        #  on key/value pairs (all must be str) since it's handled in
        #  the parent class
        #  post_update_hook is run after all mutating methods and
        #  receives no arguments
        super().__init__(initial_env=initial_env, custom_vars=custom_vars)
        if validate_item_hook is None:
            self._validate_item_hook = MonitoredEnviron._default_hook
        else:
            self._validate_item_hook = validate_item_hook
        if post_update_hook is None:
            self._post_update_hook = MonitoredEnviron._default_hook
        else:
            self._post_update_hook = post_update_hook

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key=key)
        self._post_update_hook()

    def __setitem__(self, key: str, value: str) -> None:
        self._validate_item_hook({key: value})
        super().__setitem__(key=key, value=value)
        self._post_update_hook()

    def update(self, *other, **kwargs) -> None:
        # NOTE: main constraint on keys/values (all must be str)
        # ADD DOCSTRING
        if len(other) > 1:
            raise TypeError(
                f"update expected at most 1 argument, got {len(other)}"
            )
        self._validate_item_hook(dict(other, **kwargs))
        super().update(other, **kwargs)
        self._post_update_hook()


class MonitoredList(list):
    # ADD DOCSTRING - similar to MonitoredEnviron...
    #  validate_item_hook is run before adding to or editing the list.
    #  Receives new new item(s) to be apended/inserted as a list. Not
    #  run before removing items.
    #  post_update_hook is run after all mutating methods and receives
    #  no arguments
    #  MonitoredList also disables some list methods that would lead to
    #  undesired outcomes in this use case (e.g., ability to multiply
    #  the list of modules to load by a scalar makes no sense)

    @staticmethod
    def _default_hook():
        pass

    def __init__(
            self,
            list_: Iterable[Any],
            validate_item_hook: Optional[Callable[[Any], None]] = None,
            post_update_hook: Optional[Callable[..., None]] = None
    ) -> None:
        super().__init__(list_)
        if validate_item_hook is None:
            self._validate_item_hook = MonitoredList._default_hook
        else:
            self._validate_item_hook = validate_item_hook
        if post_update_hook is None:
            self._post_update_hook = MonitoredList._default_hook
        else:
            self._post_update_hook = post_update_hook

    def __add__(self, other: List[Any]) -> List[Any]:
        for item in other:
            self._validate_item_hook(item)
        result = super().__add__(other)
        self._post_update_hook()
        return result

    def __delitem__(self, key: int) -> None:
        super().__delitem__(key)
        self._post_update_hook()

    def __iadd__(self, other: List[Any]):
        for item in other:
            self._validate_item_hook(item)
        super().__iadd__(other)
        self._post_update_hook()

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
        self._validate_item_hook(value)
        super().__setitem__(key, value)
        self._post_update_hook()

    def append(self, obj: Any) -> None:
        self._validate_item_hook(obj)
        super().append(obj)
        self._post_update_hook()

    def clear(self) -> None:
        super().clear()
        self._post_update_hook()

    def extend(self, iterable: Iterable[Any]) -> None:
        # convert to list only once in case iterable is a generator
        new_items = list(iterable)
        for item in new_items:
            self._validate_item_hook(item)
        super().extend(new_items)
        self._post_update_hook()

    def insert(self, index: int, obj: Any) -> None:
        self._validate_item_hook(obj)
        super().insert(index, obj)
        print('insert called')

    def pop(self, index: int = -1) -> Any:
        super().pop(index)
        self._post_update_hook()

    def remove(self, value: Any) -> None:
        super().remove(value)
        self._post_update_hook()
