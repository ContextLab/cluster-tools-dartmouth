from typing import Optional


class ClusterToolsError(Exception):
    pass


class SSHConnectionError(ClusterToolsError):
    def __init__(self, message: Optional[str]):
        super().__init__(message)
        self.message = message


class SSHProcessError(ClusterToolsError, ProcessLookupError):
    def __init__(self, message: Optional[str]):
        super().__init__(message)
        self.message = message
