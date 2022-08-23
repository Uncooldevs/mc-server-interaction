

class MCServerInteractionException(Exception):
    pass


class DirectoryNotEmptyException(MCServerInteractionException):
    pass


class ServerNotInstalledException(MCServerInteractionException):
    pass


class ServerAlreadyRunningException(MCServerInteractionException):
    pass
