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
    RegisterResponse,
    MegolmEvent,
    RoomMessageText,
    UnknownEvent,
)

from traffic_bot.config import Config
from traffic_bot.storage import Storage

logger = logging.getLogger(__name__)


class RegisterClient:
    def __init__(
        self,
        store: Storage,
        config: Config,
        user_id: str,
        username: str,
        password: str
    ):

        from traffic_bot.callbacks import Callbacks

        self.config = config
        self.store = store

        # Configuration options for the AsyncClient
        self.client_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=True,
        )

        self.user_id = username
        self.user_password = password
        self.user_id_without_host = user_id


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
        callbacks = Callbacks(self.client, store, config, False)
        self.client.add_event_callback(callbacks.message, (RoomMessageText,))
        self.client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
        self.client.add_event_callback(callbacks.decryption_failure, (MegolmEvent,))
        self.client.add_event_callback(callbacks.unknown, (UnknownEvent,))


    async def start(self):
        logger.info(f"Start {self.user_id}")
        

        try:
            register_response = await self.client.register(
                self.user_id_without_host,
                self.user_password,
                self.config.device_name
            )

            if type(register_response) != RegisterResponse:
                logger.error("Failed to register: %s", register_response.message)
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

        try:
            # Try to login with the configured username/password
            logger.info(f"Logged in as {self.user_id}")
            await self.client.sync(timeout=30000, full_state=True)
            await self.client.keys_upload()

        except (ClientConnectionError, ServerDisconnectedError):
            logger.warning("Unable to connect to homeserver...")        
            
        finally:
            logger.info(f"Close connection {self.user_id}")
            await self.client.close()