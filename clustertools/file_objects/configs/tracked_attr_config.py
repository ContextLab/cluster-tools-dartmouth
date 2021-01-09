from typing import (Any,
                    Callable,
                    Dict,
                    List,
                    MutableMapping,
                    NoReturn,
                    Optional,
                    TYPE_CHECKING,
                    TypeVar,
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

    @staticmethod
    def _default_update_hook(arg):
        pass

    def __init__(
            self,
            d: MutableMapping[str, Any],
            attr_update_hooks: Optional[Dict[str, Callable[[Any], None]]] = None,
            common_update_hook: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
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
            # NOTE: moving this to config_hooks for finer per-field control
            # elif not isinstance(value, type(curr_value)):
            #     raise TypeError(
            #         f"Value assigned to '{name}' must be of type "
            #         f"'{type(curr_value).__name__}'"
            #     )
            dict.__setitem__(self, name, value)

    def __setattr__(self, name: str, value: Any) -> None:
        # main self.__setattr__ exists as a wrapper to prevent multiple
        # calls to self._common_update_hook within self.update
        old_attr_val = self.__getattr__(name)
        self._setattr_helper_(name, value)
        # attr update hook needs to be run outside _setattr_helper_ so
        # updated value can be rolled back in case the hook runs some
        # validation that fails
        try:
            self._attr_update_hooks.get(name, TrackedAttrConfig._default_update_hook)(value)
        except Exception as e:
            # temporarily disable update hook while restoring original value
            _prev_attr_update_hooks = self._attr_update_hooks
            dict.__setattr__(self, '_attr_update_hooks', {})
            try:
                self._setattr_helper_(name, old_attr_val)
            finally:
                dict.__setattr__(self, '_attr_update_hooks', _prev_attr_update_hooks)
                raise e
        else:
            # only run common update hook if assignment & attr hook
            # were successful
            self._common_update_hook({name: value})

    def __setitem__(self, name: str, value: Any) -> None:
        return self.__setattr__(name, value)

    # noinspection PyPep8Naming
    def update(self, E, **F) -> None:
        # params named to match dict.update() docstring/signature
        # expensive but safe approach: prevents all changes if one
        # assignment from F fails
        E = dict(E, **F)
        pre_update = dict()
#         pre_update = self.copy()
        try:
            for key, value in E.items():
                # record each pre-self.update value...
                pre_update_key = self.__getattr__(key)
                # manually update the fields one-by-one
                self._setattr_helper_(key, value)
                # ...but don't add it to the fields to be reset in error
                # handling until running the update hook -- _setattr_helper_
                # fails for invalid assignments *before* updating value,
                # and resetting it may throw additional errors. Vs update
                # hooks fail for other validations *after* updating value,
                # and affected fields need to be rolled back.
                pre_update[key] = pre_update_key
                self._attr_update_hooks.get(key, TrackedAttrConfig._default_update_hook)(value)
        except Exception as e:
            # temporarily disable update hooks while rolling back values
            _prev_attr_update_hooks = self._attr_update_hooks
            dict.__setattr__(self, '_attr_update_hooks', {})
            try:
                for key, old_value in pre_update.items():
                    self._setattr_helper_(key, old_value)
            finally:
                dict.__setattr__(self, '_attr_update_hooks', _prev_attr_update_hooks)
                raise e from None
        else:
            # only run common update hook if all assignments &
            # attr-specific hooks were successful
            self._common_update_hook(E)

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
