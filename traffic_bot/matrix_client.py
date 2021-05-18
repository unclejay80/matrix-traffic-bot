#!/usr/bin/env python3
import asyncio
import logging
import sys
from time import sleep
from random import randrange

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

from traffic_bot.callbacks import Callbacks
from traffic_bot.config import Config
from traffic_bot.storage import Storage

logger = logging.getLogger(__name__)


class MatrixClient:
    def __init__(
        self,
        store: Storage,
        config: Config,
        master: bool
    ):
        self.config = config
        self.store = store

        # Configuration options for the AsyncClient
        self.client_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=True,
        )

        self.user_id = self.config.slave_user_id
        self.user_password = self.config.slave_password

        if master:
            self.user_id = self.config.master_user_id
            self.user_password = self.config.master_password


        # Initialize the matrix client
        self.client = AsyncClient(
            self.config.homeserver_url,
            self.user_id,
            device_id=self.config.device_id + self.user_id,
            store_path=self.config.store_path,
            config=self.client_config,
            ssl=False
        )


        # Set up event callbacks
        callbacks = Callbacks(self.client, store, config, master)
        self.client.add_event_callback(callbacks.message, (RoomMessageText,))
        self.client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
        self.client.add_event_callback(callbacks.decryption_failure, (MegolmEvent,))
        self.client.add_event_callback(callbacks.unknown, (UnknownEvent,))


    async def start(self):
        logger.info(f"Start {self.user_id}")
        asyncio.sleep(randrange(10))
        # Keep trying to reconnect on failure (with some time in-between)
        while True:
            try:
                # Try to login with the configured username/password
                try:
                    login_response = await self.client.login(
                        password=self.user_password,
                        device_name=self.config.device_name,
                    )

                    # Check if login failed
                    if type(login_response) == LoginError:
                        logger.error("Failed to login: %s", login_response.message)
                        return False
                except LocalProtocolError as e:
                    # There's an edge case here where the user hasn't installed the correct C
                    # dependencies. In that case, a LocalProtocolError is raised on login.
                    logger.fatal(
                        "Failed to login. Have you installed the correct dependencies? "
                        "https://github.com/poljar/matrix-nio#installation "
                        "Error: %s",
                        e,
                    )
                    return False

                # Login succeeded!

                logger.info(f"Logged in as {self.user_id}")
                await self.client.sync_forever(timeout=30000, full_state=True)

            except (ClientConnectionError, ServerDisconnectedError) as e:
                logger.warning("Unable to connect to homeserver, retrying in 15s...")

                # Sleep so we don't bombard the server with login requests
                sleep(1)
            finally:
                # Make sure to close the client connection on disconnect
                await self.client.close()