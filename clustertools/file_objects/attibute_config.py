from typing import Any, MutableMapping, NoReturn


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
    #   - An owner object (one with an AttributeConfig as an attribute)
    #     can define a `__getattr__` method that makes all
    #     AttributeConfig fields accessible as attributes of the owner.
    #     These proxied attribute names will *NOT* override attr/method
    #     names defined on the owner class *OR* any parent classes or
    #     mixins
    def __init__(self, d: MutableMapping[Any, Any], **kwargs) -> None:
        d.update(kwargs)
        for key, value in d.items():
            if hasattr(value, 'keys'):
                value = AttributeConfig(value)
            # using dict method directly gets around "frozen" self.__setitem__
            dict.__setitem__(self, key, value)

    def __delattr__(self, name: str) -> NoReturn:
        raise TypeError("'AttributeConfig' object does not support key deletion")

    def __delitem__(self, name: str) -> NoReturn:
        raise TypeError("'AttributeConfig' object does not support key deletion")

    def __getattr__(self, name) -> Any:
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

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setattr__(self, name, value):
        try:
            curr_value = dict.__getitem__(self, name)
        except KeyError as e:
            for _value in self.values():
                if isinstance(_value, AttributeConfig):
                    try:
                        return _value.__setattr__(name, value)
                    except KeyError:
                        continue
                    except AttributeError:
                        raise
            else:
                raise e
        else:
            if isinstance(curr_value, AttributeConfig):
                raise AttributeError("'AttributeConfig' subsections do not support assignment, only individual values")
            return dict.__setitem__(self, name, value)

    def __setitem__(self, name, value):
        return self.__setattr__(name, value)