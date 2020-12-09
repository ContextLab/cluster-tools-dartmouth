from typing import Any, Callable, MutableMapping, NoReturn, Optional


class AttributeConfig(dict):
    # ADD DOCSTRING
    # a dict-like mapping used (in this instance) for proxying global
    # and project config files within the larger Config object. Allows
    # config files to be hierarchically structured without requiring
    # verbose indexing to get/set values. Features include:
    #   - dict items are accessible using attribute access notation,
    #     i.e., `my_dict.somekey` works the same as `my_dict["somekey"]`
    #   - this works recursively so it can be chained, e.g.,
    #     `my_dict.outerkey.middlekey.innerkey` works in addition to
    #     `my_dict["outerkey"]["middlekey"]["innerkey"]`
    #   - all keys are available as top-level attributes regardless of
    #     nesting level, except for those whose values are also
    #     AttributeConfigs. This is proactively disallowed
    #     (see `self.__getattr__`) to keep the interface from getting
    #     *too* confusing. The idea is that you can set nested values
    #     without overly verbose indexing, e.g., `my_dict.innerkey = 1`
    #     works for `my_dict["outerkey"]["middlekey"]["innerkey"] = 1`,
    #     but `my_dict.middle_key.innerkey` does not (raises `KeyError`)
    #   - Keys are immutable but values are mutable, so the user can
    #     update config fields but can't delete them or add new ones
    #   - Updated values assigned to fields must be the same type as the
    #     original
    #   - An owner object (one with an AttributeConfig as an attribute)
    #     can define a `__getattr__` method that makes all
    #     AttributeConfig fields accessible as attributes of the owner.
    #     These proxied attribute names will *NOT* override attr/method
    #     names defined on the owner class *OR* any parent classes or
    #     mixins

    @staticmethod
    def _default_config_update_hook():
        pass

    def __init__(
            self,
            d: MutableMapping[Any, Any],
            update_hook: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(d)
        for key, value in d.items():
            if hasattr(value, 'keys') and key != 'environ':
                value = AttributeConfig(value, update_hook=update_hook)
            # using dict methods directly to get around "frozen" self.__setitem__
            dict.__setitem__(self, key, value)
        if update_hook is None:
            update_hook = AttributeConfig._default_config_update_hook
        dict.__setattr__(self, '_config_update_hook', update_hook)

    def __delattr__(self, name: str) -> NoReturn:
        raise TypeError("'AttributeConfig' object does not support key deletion")

    def __delitem__(self, name: str) -> NoReturn:
        raise TypeError("'AttributeConfig' object does not support key deletion")

    def __getattr__(self, name: str) -> Any:
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            for value in self.values():
                if isinstance(value, AttributeConfig):
                    try:
                        val = value.__getattr__(name)
                    except KeyError:
                        continue
                    else:
                        if isinstance(val, AttributeConfig):
                            continue
                        return val
            else:
                raise KeyError(f"No option named '{name}' found") from None

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __setattr_helper_(self, name, value):
        # contains all of the "real" self.__setattr__ machinery
        try:
            curr_value = dict.__getitem__(self, name)
        except KeyError as e:
            for _value in self.values():
                if isinstance(_value, AttributeConfig):
                    try:
                        return _value.__setattr_helper_(name, value)
                    except KeyError:
                        continue
                    except (AttributeError, TypeError):
                        raise
            else:
                raise TypeError("'AttributeConfig' object does not support "
                                "key insertion") from e
        else:
            if isinstance(curr_value, AttributeConfig):
                raise AttributeError("'AttributeConfig' subsections do not "
                                     "support assignment, only individual values")
            elif not isinstance(value, type(curr_value)):
                raise TypeError(f"Value assigned to '{name}' must be of type "
                                f"'{type(curr_value).__name__}'")
            return dict.__setitem__(self, name, value)

    def __setattr__(self, name, value):
        # main self.__setattr__ exists as a wrapper to prevent multiple
        # calls to self._config_update_hook within self.update
        try:
            self.__setattr_helper_(name, value)
        except:
            raise
        else:
            self._config_update_hook()

    def __setitem__(self, name: str, value: Any) -> None:
        return self.__setattr__(name, value)

    # noinspection PyPep8Naming
    def update(self, E, **F) -> None:
        # params named to match dict.update() docstring/signature
        # expensive but safe approach, prevents all changes if one assignment from F fails
        E = dict(E, **F)
        pre_update = dict()
        try:
            for key, value in E.items():
                # record each pre-self.update value
                pre_update[key] = self.__getattr__(key)
                # manually update the fields one-by-one
                self.__setattr_helper_(key, value)
        except Exception:
            # if any assignment fails, restore already-updated fields
            # remove the problem key (if recorded) so we don't raise another AttributeError
            pre_update.pop(key, None)
            for key, old_value in pre_update.items():
                dict.__setattr__(self, key, old_value)
            raise
        else:
            self._config_update_hook()

    def setdefault(self, key: Any, default: Optional[Any] = None) -> NoReturn:
        raise TypeError("'AttributeConfig' object does not support key insertion")
