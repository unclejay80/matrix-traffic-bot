import time
import threading
import asyncio
import random
import string
import logging


from nio import AsyncClient, MatrixRoom, RoomMessageText, RoomKickError

from traffic_bot.chat_functions import react_to_event, send_text_to_room, room_invite, room_kick, register, login
from traffic_bot.config import Config
from traffic_bot.storage import Storage


logger = logging.getLogger(__name__)

class Command:
    def __init__(
        self,
        client: AsyncClient,
        store: Storage,
        config: Config,
        command: str,
        room: MatrixRoom,
        event: RoomMessageText
    ):
        """A command made by a user.

        Args:
            client: The client to communicate to matrix with.

            store: Bot storage.

            config: Bot configuration parameters.

            command: The command and arguments.

            room: The room the command was sent in.

            event: The event describing the command.
        """
        self.client = client
        self.store = store
        self.config = config
        self.command = command
        self.room = room
        self.event = event
        self.args = self.command.split()[1:]


    async def makeTraffic(self, client, roomId):
        while True:
            await send_text_to_room(client, roomId, "response")
            time.sleep(5)


    async def process(self):
        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("react"):
            await self._react()
        elif self.command.startswith("help"):
            await self._show_help()
        elif self.command.startswith("kick_invite"):
            await self._kick_invite()
        elif self.command.startswith("invite"):
            await self._invite()
        elif self.command.startswith("add_zombie"):
            await self._add_zombie()
        else:
            await self._unknown_command()


    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)

        #await self.makeTraffic(self.client, self.room.room_id)

        try:
            for x in range(0, int(response)):
                await send_text_to_room(self.client, self.room.room_id, str(x))
        except:
            pass

    async def _react(self):
        """Make the bot react to the command message"""
        # React with a start emoji
        reaction = "⭐"
        await react_to_event(
            self.client, self.room.room_id, self.event.event_id, reaction
        )


    async def _invite(self):
        """ Invite x slaves into current room """
        slaveCnt = " ".join(self.args)

        start = self.config.slave_index_start
        end = start + int(slaveCnt)
        if end > self.config.slave_index_end:
            end = self.config.slave_index_end

        try:
            for x in range(start, end):
                userId = self.config.slave_base_user_id + str(x) + ":" + self.config.homeserver_host
                try:
                    await room_invite(self.client, self.room.room_id, userId)
                except:
                    pass
        except:
            pass


    async def _kick_invite(self):
        slaveId = " ".join(self.args)

        userId = self.config.slave_base_user_id + slaveId + ":" + self.config.homeserver_host
        try:
            room_kick_response = await room_kick(self.client, self.room.room_id, userId)

            if type(room_kick_response) == RoomKickError:
                logger.error("Failed to kick: %s", room_kick_response.message)
                return

            await room_invite(self.client, self.room.room_id, userId)
        except:
            pass



    async def _add_zombie(self):
        """ Add zombie user to current room. New User will be registered and invited but does not sync anymore"""
        slaveCnt = " ".join(self.args)

        try:
            random_user_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            for x in range(0, int(slaveCnt)):
                userId = "zombie_" + random_user_id + "_" + str(x)
                try:
                    userIdFull = "@" + userId + ":" + self.config.homeserver_host

                    inviteResponse = await room_invite(self.client, self.room.room_id, userIdFull)

                    event_loop = asyncio.get_event_loop()
                    asyncio.ensure_future(register(self.config, userId, userIdFull, "password"), loop=event_loop)
                except:
                    pass
        except:
            pass



    async def _show_help(self):
        """Show the help text"""
        if not self.args:
            text = (
                "Hello, I am a bot made with matrix-nio! Use `help commands` to view "
                "available commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "rules":
            text = "These are the rules!"
        elif topic == "commands":
            text = "Available commands:"
        else:
            text = "Unknown help topic!"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )
