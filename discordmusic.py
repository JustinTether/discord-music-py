# This example covers advanced startup options and uses some real world examples for why you may need them.

import asyncio
import logging
import logging.handlers
import json
import os

from typing import List, Optional

import discord
from discord.ext import commands

SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True

def LoadSettings():
    settings = {}

    with open(SETTINGS_FILE, "r") as settings_file:
         settings = json.load(settings_file)

    return settings

def GetSpotifyCreds(cred_path):
    creds = {}
    with open(cred_path, "r") as json_file:
        creds = json.load(json_file)

    return creds

def GetToken(token_path):
    with open(token_path, "r") as token_file:
        return token_file.readlines()[0]

class CustomBot(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        testing_guild_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = initial_extensions

    async def setup_hook(self) -> None:

        # here, we are loading extensions prior to sync to ensure we are syncing interactions defined in those extensions.

        for extension in self.initial_extensions:
            await self.load_extension(extension)

        # In overriding setup hook,
        # we can do things that require a bot prior to starting to process events from the websocket.
        # In this case, we are using this to ensure that once we are connected, we sync for the testing guild.
        # You should not do this for every guild or for global sync, those should only be synced when changes happen.
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            # We'll copy in the global commands to test with:
            self.tree.copy_global_to(guild=guild)
            # followed by syncing to the testing guild.
            await self.tree.sync(guild=guild)

        # This would also be a good place to connect to our database and
        # load anything that should be in memory prior to handling events.


async def main():

    # When taking over how the bot process is run, you become responsible for a few additional things.

    # 1. logging

    # for this example, we're going to set up a rotating file logger.
    # for more info on setting up logging,
    # see https://discordpy.readthedocs.io/en/latest/logging.html and https://docs.python.org/3/howto/logging.html

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    exts = ['cogs.music']
    async with CustomBot("!", initial_extensions=exts, intents=intents) as bot:
        settings = LoadSettings()
        await bot.start(GetToken(settings['discord_token']))


asyncio.run(main())



