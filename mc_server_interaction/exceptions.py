class MCServerInteractionException(Exception):
    pass


class DirectoryNotEmptyException(MCServerInteractionException):
    pass


class ServerNotInstalledException(MCServerInteractionException):
    pass


class ServerRunningException(MCServerInteractionException):
    pass


class UnsupportedVersionException(MCServerInteractionException):
    pass


class NotAWorldFolderException(MCServerInteractionException):
    pass


class WorldExistsException(MCServerInteractionException):
    pass
