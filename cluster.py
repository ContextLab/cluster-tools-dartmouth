import getpass
import os

import spur
import spurplus


class Cluster:
    def __init__(
            self,
            hostname,
            username=None,
            password=None,
            use_key=False,
            port=22,
            timeout=60,
            retries=0,
            retry_delay=1,
            shell=None,
            cwd=None,
            env_additions=None
    ):
        # setup connection first for fast failure
        if hostname == 'localhost':
            self.shell = spur.LocalShell()
            self.username = getpass.getuser()
            self.port = None
            self.environ = dict(os.environ)
        else:
            self.shell = spurplus.connect_with_retries(
                hostname=hostname,
                username=username,
                password=(getpass.getpass('Password: ') if not (use_key or password) else password),
                look_for_private_keys=(not use_key),
                port=port,
                connect_timeout=timeout,
                retries=retries,
                retry_period=retry_delay
            )
            self.username = username
            self.port = port
            env_str = self.shell.run(['printenv']).output.split('\nBASH_FUNC_module()')[0]
            self.environ = dict(map(lambda x: x.split('=', 1), env_str.splitlines()))

        del password

        self.hostname = hostname
        self.env_additions = env_additions or dict()
        self.environ.update(self.env_additions)
        self.HOME = self.environ.get('HOME')

        if cwd is None:
            self._CWD = self.HOME
        else:
            self.CWD = cwd

        if shell is None:
            self._SHELL = self.environ.get('SHELL')
        else:
            self.SHELL = shell

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.shell.__exit__(*args)

    @property
    def CWD(self):
        return self._CWD

    @CWD.setter
    def CWD(self, new_cwd):
        if not new_cwd.startswith('/'):
            raise AttributeError('working directory must be an absolute path')
        try:
            assert self.shell.is_dir(new_cwd)
        except (AssertionError, FileNotFoundError) as e:
            if isinstance(e, AssertionError):
                reason = f"Path points to a file"
            else:
                reason = f"Path does not exist"
            raise AttributeError("Can't set working directory to "
                                 f"{new_cwd}. {reason}")
        else:
            self._CWD = new_cwd
            self.environ['PWD'] = self._CWD

    @property
    def SHELL(self):
        return self._SHELL

    @SHELL.setter
    def SHELL(self, new_shell):
        shells_avail = self.shell.run(['cat', '/etc/shells']).output.splitlines()
        if new_shell in shells_avail:
            self._SHELL = new_shell
        else:
            try:
                first_match = [s.split(['/'])[-1] for s in shells_avail].index(new_shell)
                self._SHELL = shells_avail[first_match]
            except IndexError:
                raise AttributeError(f"No executable found for {new_shell}. "
                                     f"Available shells are:\n{', '.join(shells_avail)}")
        self.environ['SHELL'] = self._SHELL

    def getenv(self, var, default=None):
        return self.environ.get(var, default=default)

    def putenv(self, var, value):
        self.environ[var] = value

    def unsetenv(self, var):
        self.environ.pop(var)

