from typing import Callable, Dict, Literal, Optional, Union, Sequence

# TODO: pretty sure this is going to be a circular import...
from clustertools.shared.typing import EnvMapping


class PseudoEnviron:
    # ADD DOCSTRING
    # TODO: because of how the temporary env variables are set
    #  (https://github.com/mwilliamson/spur.py/blob/31efe77f04839b13e408b6461948cc1f2b75017b/spur/ssh.py#L87),
    #  it may be more efficient to make self.current_env a property that
    #  returns only the differences from self.initial_env.
    # TODO: current unsetenv approach doesn't work. Could:
    #   - try using an empty string (single quotes?) to get FOO=
    #   - prepend `env -u SOMEVAR` to the command
    #   - prepend `env -i` to all commands and export full current_env
    #   - prepend an `unset` call to the full command
    def __init__(self, initial_env: EnvMapping, custom_vars: EnvMapping):
        self._initial_env = initial_env
        self._current_env = initial_env.copy()
        self._current_env.update(custom_vars)

    def __contains__(self, item):
        return item in self._current_env

    def __delitem__(self, key):
        del self._current_env[key]

    def __getattr__(self, item):
        try:
            return getattr(self._current_env, item)
        except AttributeError as e:
            raise AttributeError("'PseudoEnviron' object has no attribute "
                                 f"'{item}'") from e

    def __getitem__(self, key):
        return self._current_env[key]

    def __repr__(self):
        return repr(self._current_env)

    # explicitly overridden methods for coercing keys/values to str
    def __setitem__(self, key, value):
        if not (isinstance(key, str) and isinstance(value, str)):
            raise TypeError("All keys and values in mapping must be 'str'")
        self._current_env[key] = value

    # noinspection PyPep8Naming
    def update(self, E, **F) -> None:
        # ADD DOCSTRING
        # params named to match dict.update() signature
        E = dict(E, **F)
        if not all(isinstance(i, str) for i in sum(E.items(), ())):
            raise TypeError("All keys and values in mapping must be 'str'")
        # intentionally *DOESN'T* call self.__setitem__ to avoid
        # repeated type checks + callback runs in subclass
        self._current_env.update(**E)

    def setdefault(self, key: str, default: str = '') -> str:
        # ADD DOCSTRING
        if key not in self:
            self[key] = default
        return self[key]

    def reset(
            self,
            key: str,
            if_custom: Literal['remove', 'keep', 'raise'] = 'remove'
    ) -> None:
        # ADD DOCSTRING
        # TODO: test all combinations of conditions for this
        # options for 'if_custom': remove, keep, raise
        if key in self._initial_env:
            self._current_env[key] = self._initial_env[key]
        elif if_custom == 'raise':
            raise KeyError(f"Environment variable '{key}' was not set "
                           f"before shell was initialized")
        elif key not in self._current_env:
            # throw error regardless of `if_custom`
            raise KeyError(f"'{key}' does not exist in either the "
                           f"current or initial environment")
        elif if_custom == 'remove':
            self._current_env.pop(key)
        elif if_custom != 'keep':
            raise ValueError(f"Invalid option '{if_custom}' for "
                             "'if_custom'. Must be one of: {'remove', "
                             "'keep', 'raise'}")

    def reset_all(self) -> None:
        # ADD DOCSTRING
        self._current_env = self._initial_env


class MonitoredEnviron(PseudoEnviron):
    # ADD DOCSTRING

    @staticmethod
    def _default_update_hook():
        pass

    def __init__(
            self,
            initial_env: EnvMapping,
            custom_vars: EnvMapping,
            update_hook: Optional[Callable[[], None]] = None,
    ):
        # ADD DOCSTRING
        super().__init__(initial_env=initial_env, custom_vars=custom_vars)
        if update_hook is None:
            self.update_hook = MonitoredEnviron._default_update_hook
        else:
            self.update_hook = update_hook

    def __delitem__(self, key):
        super().__delitem__(key=key)
        self.update_hook()

    def __setitem__(self, key, value):
        super().__setitem__(key=key, value=value)
        self.update_hook()

    # noinspection PyPep8Naming
    def update(self, E, **F):
        super().update(E, **F)
        self.update_hook()
