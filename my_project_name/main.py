#!/usr/bin/env python3
import asyncio
import logging
import sys
from time import sleep


from aiohttp import ClientConnectionError, ServerDisconnectedError
from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LocalProtocolError,
    LoginError,
    MegolmEvent,
    RoomMessageText,
    UnknownEvent,
)

from my_project_name.callbacks import Callbacks
from my_project_name.config import Config
from my_project_name.storage import Storage
from my_project_name.matrix_client import MatrixClient

logger = logging.getLogger(__name__)


async def main():
    """The first function that is run when starting the bot"""

    # Read user-configured options from a config file.
    # A different config file path can be specified as the first command line argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.yaml"


    clientList = []


    # create admin

    config = Config(config_path, "")

    store = Storage(config.database)
    client = MatrixClient(store, config, True)
    clientList.append(client)


    start = int(config.slave_index_start)
    end = int(config.slave_index_end)

    # create slaves
    for x in range(start, end):
        # Read the parsed config file and create a Config object
        config = Config(config_path, str(x))

        store = Storage(config.database)
        client = MatrixClient(store, config, False)
        clientList.append(client)

        logger.info(f"main loop " + str(x))

    logger.info(f"main 2")

    await asyncio.gather(
        *[it.start() for it in clientList])
    



# Run the main function in an asyncio event loop
asyncio.get_event_loop().run_until_complete(main())
