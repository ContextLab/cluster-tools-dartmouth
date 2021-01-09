from typing import (Any,
                    Callable,
                    Dict,
                    List,
                    MutableMapping,
                    NoReturn,
                    Optional,
                    TYPE_CHECKING,
                    Union)

from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList

if TYPE_CHECKING:
    _AsDict = Dict[str, Union[str, bool, int, List[str], Dict[str, str], '_AsDict']]


class TrackedAttrConfig(dict):
    # ADD DOCSTRING
    # a dict-like mapping used (in this instance) for proxying global
    # and project config files within the larger Config object. Allows
    # config files to be hierarchically structured without requiring
    # verbose indexing to get/set values. Features include:
    #   - dict items are accessible using attribute access notation,
    #     i.e., `my_dict.a` works the same as `my_dict["a"]`
    #   - this also works recursively for chained attribute-style
    #     access. E.g., `my_dict.a.b.c` returns the value stored in
    #     `my_dict["a"]["b"]["c"]`.
    #   - in addition to chained access, all fields are accessible as
    #     both attributes and keys on the top-level object, regardless
    #     of nesting. E.g., `my_dict["a"]["b"]["c"]` may also be
    #     accessed via both `my_dict["c"]` and `my_dict.c`.
    #       + NOTE: attribute/key access to arbitrarily nested dict keys
    #         is performed by first checking each key, then recursively
    #         searching each value **depth-first, in insertion order**.
    #         This has important implications for how duplicate keys are
    #         handled:
    #           1. Keys in the top-level dict are always preferred over
    #              those in nested dicts. E.g., for a TrackedAttrConfig
    #              containing both `my_dict["a"]` and
    #              `my_dict["b"]["a"]`, `my_dict["a"]` and `my_dict.a`
    #              will always return the former.
    #           2. For a TrackedAttrConfig containing both
    #              `my_dict["a"]["e"]` and `my_dict["b"]["c"]["d"]["e"]`,
    #              the value returned by `my_dict`["e"]` and `my_dict.e`
    #              depends on whether `"a"` or `"b"` was added to
    #              `my_dict` first. If insertion order were unknown,
    #              `my_dict.b.e`, `my_dict.b.c.e`, `my_dict.b.c.d.e`,
    #              and their equivalents in dict-like indexing would all
    #              guarantee returning `my_dict["b"]["c"]["d"]["e"]`.
    #              Additionally, `str(my_dict)` and `repr(my_dict)`
    #              always display items in insertion order, top-down.
    #           3. Two keys of the same name must share an attribute
    #              update hook.
    #   - Keys are immutable but values are mutable, so the user can
    #     update config fields but can't delete them or add new ones
    #   - Updated values assigned to fields must be the same type as the
    #     original
    #   - An owner object (one with an TrackedAttrConfig as an attribute)
    #     can define a `__getattr__` method that makes all
    #     TrackedAttrConfig fields accessible as attributes of the owner.
    #     These proxied attribute names will *NOT* override attr/method
    #     names defined on the owner class *OR* any parent classes or
    #     mixins

    def __init__(
            self,
            d: MutableMapping[str, Any],
            attr_update_hooks: Optional[Dict[str, Callable[[Any], Any]]] = None,
            common_update_hook: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        # ADD DOCSTRING
        super().__init__(d)
        for key, value in d.items():
            if hasattr(value, 'keys') and key != 'environ':
                value = TrackedAttrConfig(value,
                                          attr_update_hooks=attr_update_hooks,
                                          common_update_hook=common_update_hook)
            # using dict methods directly to get around "frozen" self.__setitem__
            dict.__setitem__(self, key, value)
        if attr_update_hooks is None:
            attr_update_hooks = dict()
        dict.__setattr__(self, '_attr_update_hooks', attr_update_hooks)
        if common_update_hook is None:
            common_update_hook = TrackedAttrConfig._default_update_hook
        dict.__setattr__(self, '_common_update_hook', common_update_hook)

    def __delattr__(self, name: str) -> NoReturn:
        raise TypeError("'TrackedAttrConfig' object does not support key deletion")

    def __delitem__(self, name: str) -> NoReturn:
        raise TypeError("'TrackedAttrConfig' object does not support key deletion")

    def __getattr__(self, name: str) -> Any:
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            for value in self.values():
                if isinstance(value, TrackedAttrConfig):
                    try:
                        return value.__getattr__(name)
                    except KeyError:
                        continue
            else:
                raise KeyError(f"No option named '{name}' found") from None

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def _setattr_helper_(self, name: str, value: Any) -> None:
        # contains all of the "real" self.__setattr__ machinery
        try:
            curr_value = dict.__getitem__(self, name)
        except KeyError:
            for i, _value in enumerate(self.values()):
                if isinstance(_value, TrackedAttrConfig):
                    try:
                        return _value._setattr_helper_(name, value)
                    except KeyError:
                        continue
                    except AttributeError as e:
                        raise e from None
                    except TypeError as e:
                        if i == len(self.values()):
                            raise e from None
                        else:
                            continue
            else:
                raise TypeError(
                    "'TrackedAttrConfig' object does not support key insertion"
                ) from None
        else:
            if isinstance(curr_value, TrackedAttrConfig):
                raise AttributeError(
                    "'TrackedAttrConfig' subsections do not support "
                    "assignment, only individual values"
                )
            dict.__setitem__(self, name, value)

    def __setattr__(self, name: str, value: Any) -> None:
        # main 'self.__setattr__' method is really just a wrapper around
        # 'self._setattr_helper' so that 'self.update' and recursive
        # attribute lookup don't trigger multiple calls to the two
        # update hooks
        value = self._attr_update_hooks[name](value)
        self._setattr_helper_(name, value)
        self._common_update_hook({name: value})

    def __setitem__(self, name: str, value: Any) -> None:
        return self.__setattr__(name, value)

    def update(self, *other, **kwargs) -> None:
        update_vals = dict(*other, **kwargs)
        update_vals = {
            k: self._attr_update_hooks[k](v) for k, v in update_vals.items()
        }
        for key, value in update_vals.items():
            self._setattr_helper_(key, value)
        self._common_update_hook(update_vals)

    def setdefault(self, key: Any, default: Optional[Any] = None) -> NoReturn:
        raise TypeError("'TrackedAttrConfig' object does not support key insertion")

    def to_dict(self) -> _AsDict:
        d = dict(self)
        for key, value in d.items():
            if isinstance(value, MonitoredList):
                d[key] = list(value)
            elif isinstance(value, MonitoredEnviron):
                d[key] = dict(value)
            elif isinstance(value, TrackedAttrConfig):
                d[key] = value.to_dict()
        return d
