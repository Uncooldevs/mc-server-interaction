__version__ = "0.3.0"
__app_name__ = "mc-server-interaction"

from mc_server_interaction.utils.singleton import SingleInstance

singleton = SingleInstance()

import mc_server_interaction.log as log

log.setup_logging()
