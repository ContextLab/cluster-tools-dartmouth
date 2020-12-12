from typing import Any, Callable, Dict, MutableMapping, NoReturn, Optional


class TrackedAttrConfig(dict):
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
    #     TrackedAttrConfigs. This is proactively disallowed
    #     (see `self.__getattr__`) to keep the interface from getting
    #     *too* confusing. The idea is that you can set nested values
    #     without overly verbose indexing, e.g., `my_dict.innerkey = 1`
    #     works for `my_dict["outerkey"]["middlekey"]["innerkey"] = 1`,
    #     but `my_dict.middle_key.innerkey` does not (raises `KeyError`)
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
            common_update_hook: Optional[Callable[[Dict[str, any]], None]] = None
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
                        val = value.__getattr__(name)
                    except KeyError:
                        continue
                    else:
                        if isinstance(val, TrackedAttrConfig):
                            continue
                        return val
            else:
                raise KeyError(f"No option named '{name}' found") from None

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def _setattr_helper_(self, name, value):
        # contains all of the "real" self.__setattr__ machinery
        try:
            curr_value = dict.__getitem__(self, name)
        except KeyError:
            for _value in self.values():
                if isinstance(_value, TrackedAttrConfig):
                    try:
                        return _value._setattr_helper_(name, value)
                    except KeyError:
                        continue
                    except (AttributeError, TypeError) as e:
                        raise e from None
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
            elif not isinstance(value, type(curr_value)):
                raise TypeError(
                    f"Value assigned to '{name}' must be of type "
                    f"'{type(curr_value).__name__}'"
                )
            dict.__setitem__(self, name, value)

    def __setattr__(self, name, value):
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
        print('staring update')
        # params named to match dict.update() docstring/signature
        # expensive but safe approach: prevents all changes if one
        # assignment from F fails
        E = dict(E, **F)
        pre_update = dict()
#         pre_update = self.copy()
        try:
            for key, value in E.items():
                print(f'===== setting {key} to {value} =====')
                print(f'before:\n\t{self}')
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
                print(f'after:\n\t{self}', end='\n\n')
        except Exception as e:
            # temporarily disable update hooks while rolling back values
            print('setting temporary attr update hooks')
            _prev_attr_update_hooks = self._attr_update_hooks
            dict.__setattr__(self, '_attr_update_hooks', {})
            try:
                for key, old_value in pre_update.items():
                    print(f'===== resetting {key} to {old_value} =====')
                    print(f'before:\n\t{self}')
                    self._setattr_helper_(key, old_value)
                    print(f'after:\n\t{self}', end='\n\n')
            finally:
                print('restoring attr update hooks')
                dict.__setattr__(self, '_attr_update_hooks', _prev_attr_update_hooks)
                raise e from None
        else:
            # only run common update hook if all assignments &
            # attr-specific hooks were successful
            self._common_update_hook(E)

    def setdefault(self, key: Any, default: Optional[Any] = None) -> NoReturn:
        raise TypeError("'TrackedAttrConfig' object does not support key insertion")
