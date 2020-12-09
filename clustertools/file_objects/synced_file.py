import hashlib
from pathlib import Path, PurePosixPath
from typing import Optional

from clustertools.cluster import Cluster
from clustertools.shared.exceptions import SSHConnectionError
from clustertools.shared.typing import PathLike

# TODO: remove NotImplementedErrors once finished writing
class SyncedFile:
    # ADD DOCSTRING
    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike = None,
            remote_path: Optional[PathLike] = None
    ):
        # ADD DOCSTRING
        super().__init__()
        self._cluster = cluster
        self._local_path = None
        self._remote_path = None

        if local_path is not None:
            self.local_path = local_path
        if remote_path is not None:
            self.remote_path = remote_path

    @property
    def local_path(self) -> Path:
        # ADD DOCSTRING
        return self._local_path

    @local_path.setter
    def local_path(self, path: PathLike):
        if self._local_path is not None:
            raise AttributeError("local/remote path mapping is "
                                 "read-only once set")
        path = self._cluster._resolve_path_local(Path(path), strict=False)
        self._local_path = path
        self._init_local()

    @property
    def remote_path(self) -> PurePosixPath:
        # ADD DOCSTRING
        return self._remote_path

    @remote_path.setter
    def remote_path(self, path: PathLike):
        if self._remote_path is not None:
            raise AttributeError("local/remote path mapping is "
                                 "read-only once set")
        elif not self._cluster.connected:
            raise SSHConnectionError("Connection to remote host must be "
                                     "open to assign a remote path to a "
                                     "file mapping")
        path = self._cluster.resolve_path(PurePosixPath(path), strict=False)
        self._remote_path = path
        self._init_remote()

    @property
    def md5sum_local(self) -> str:
        # ADD DOCSTRING
        hash_md5 = hashlib.md5()
        with self.local_path.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @property
    def md5sum_remote(self) -> str:
        # ADD DOCSTRING
        if hasattr(self, 'project'):
            return self.project.cluster.shell.md5(self.remote_path)
        elif hasattr(self, 'cluster'):
            return self.cluster.shell.md5(self.remote_path)
        else:
            raise NotImplementedError("Not supported for objects not "
                                      "associated with a 'cluster' object")

    @property
    def is_synced(self):
         return self.md5sum_local == self.md5sum_remote

    def _init_local(self):
        # method that takes no action by default, but may be overridden
        # in subclasses to set specific behaviors on object creation
        pass

    def _init_remote(self):
        # may be overridden in subclasses to set specific behaviors on
        # local/remote mapping creation. By default, syncs the two files
        if not self._cluster.is_file(self.remote_path) or not self.is_synced:
            # TODO: reorder attr assignment in self.__init__ so that
            #  when global config is initialized, self.sync() can be run
            #  here with preferred sync method (local/remote/recent)
            self.upload()

    def upload(self) -> None:
        if hasattr(self, 'project'):
            put = self.project.cluster.shell.put
        elif hasattr(self, 'cluster'):
            put = self.cluster.shell.put
        else:
            raise NotImplementedError("Not supported for objects not "
                                      "associated with a 'cluster' object")

        return put(local_path=self.local_path,
                   remote_path=self.remote_path,
                   create_directories=False,
                   consistent=True)

    def sync(self):
        # ADD DOCSTRING
        # TODO: add option to "prefer" local, remote, or most recently
        #  edited version of file
        if not self.is_synced:
            self.upload()
