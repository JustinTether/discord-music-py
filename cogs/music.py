# This was all thanks to the wide-cock chad at https://github.com/Devoxin/Lavalink.py
# As well, this mans showed me tekore where we can turn spotify links into a 
"""
This example cog demonstrates basic usage of Lavalink.py, using the DefaultPlayer.
As this example primarily showcases usage in conjunction with discord.py, you will need to make
modifications as necessary for use with another Discord library.
Usage of this cog requires Python 3.6 or higher due to the use of f-strings.
Compatibility with Python 3.5 should be possible if f-strings are removed.
"""
import re

import json
import discord
import tekore as tk
import lavalink
from discord.ext import commands
from lavalink.filters import LowPass

url_rx = re.compile(r'https?:\/\/(?:www\.)?.+')
spotify_rx = re.compile(r'https?:\/\/open.spotify.com(?:www\.)?.+')

SETTINGS_FILE = "settings.json"
DEFAULT_VOLUME_LEVEL = 50



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

settings = LoadSettings()
creds = GetSpotifyCreds(settings["spotify_creds"])

app_token = tk.request_client_token(creds['client_id'], creds['secret'])
spotify_client = tk.Spotify(app_token)


async def ConvertSpotifyPlaylist(self, ctx, player, query):
    track_links = []

    playlist_id = tk.from_url(query)

    try:
        playlist = spotify_client.playlist(playlist_id[1])
    except:
        await ctx.send("The playlist link is invalid, unable to load playlistl links", delete_after=60)
        
    for track in playlist.tracks.items:
        query = f"ytsearch: {track.track.name} {track.track.artists[0].name}"
        results = await player.node.get_tracks(query)
        print(f"Querying for song: {query}")
        if results is None:
            await ctx.send(f"Unable to find track for song: {query}")
        
        track_links.append(results.tracks[0])

    print(f"Current list of tracks to be added: {track_links}")
    return track_links



class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                'localhost',
                2333,
                'youshallnotpass',
                'us',
                'default-node'
            )
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('127.0.0.1', 2333, 'youshallnotpass', 'us', 'default-node')  # Host, Port, Password, Region, Name

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()
        with open(SETTINGS_FILE, "w") as settings_file:
            settings_file.write(json.dumps(settings, indent=4))         
        

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc.

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)

        
        # Sets the default volume based on our settings JSON, this is to ensure that the bot isn't _too loud_ when it first enters a chat!
        # this volume can be overridden by using the !volume command -- We should also be saving these settings as per-guild settings --
        # We can use the ctx.guild.id to store this in a settings dict which could be serialized out
        if ctx.guild.id in settings["guild_settings"]:
            await player.set_volume(settings["guild_settings"][ctx.guild.id]["default_volume"])
        else:
            await player.set_volume(settings["default_volume"])
        
        

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('play',)

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError("I can't play you music unless you're in a voice channel first!")

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError("Sorry, only those in my voice channel can use commands")

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To be polite, we can tell the bot to disconnect from the voicechannel.
            guild_id = event.player.guild_id
            guild = self.bot.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)



    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        """ Searches and plays a song from a given query. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        embed = discord.Embed(color=discord.Color.blurple())

        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # If this IS a url match, check to see if this is a spotify match
        # If it's a spotify match we use the spotify web api to get track information and do a youtube search
        # It's not quite the same as spotify itself, but we _can't_ actually stream a spotify link
        if spotify_rx.match(query):
            if "/playlist/" in query:
                tracks = await ConvertSpotifyPlaylist(self, ctx, player, query)

                for track in tracks:
                    # Add all of the tracks from the playlist to the queue.
                    print(f"adding song to queue: {track.title}")

                    player.add(requester=ctx.author.id, track=track)

                    if not player.is_playing:
                        await player.play()

                    
                embed.title = 'Playlist queued!'
                embed.description = f'Spotify playlist of - {len(tracks)} tracks queued! \n Queued by: {ctx.author.name}'
                await ctx.send(embed=embed)

                return

            else:
                trackID = tk.from_url(query)
                track = spotify_client.track(trackID[1])

                query = f"{track.artists[0].name}: {track.name}"
                query = f'ytsearch:{query}'

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
        if not results or not results.tracks:
            return await ctx.send('Nothing found!')

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == 'PLAYLIST_LOADED':
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = 'Track queued'
            embed.description = f'[{track.title}]({track.uri})'

            player.add(requester=ctx.author.id, track=track)

        await ctx.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @commands.command(aliases=['lp'])
    async def lowpass(self, ctx, strength: float):
        """ Sets the strength of the low pass filter. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # This enforces that strength should be a minimum of 0.
        # There's no upper limit on this filter.
        strength = max(0.0, strength)

        # Even though there's no upper limit, we will enforce one anyway to prevent
        # extreme values from being entered. This will enforce a maximum of 100.
        strength = min(100, strength)

        embed = discord.Embed(color=discord.Color.blurple(), title='Low Pass Filter')

        # A strength of 0 effectively means this filter won't function, so we can disable it.
        if strength == 0.0:
            await player.remove_filter('lowpass')
            embed.description = 'Disabled **Low Pass Filter**'
            return await ctx.send(embed=embed)

        # Lets create our filter.
        low_pass = LowPass()
        low_pass.update(smoothing=strength)  # Set the filter strength to the user's desired level.

        # This applies our filter. If the filter is already enabled on the player, then this will
        # just overwrite the filter with the new values.
        await player.set_filter(low_pass)

        embed.description = f'Set **Low Pass Filter** strength to {strength}.'
        await ctx.send(embed=embed)

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not ctx.voice_client:
            # We can't disconnect, if we're not connected.
            return await ctx.send('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await ctx.send('You\'re not in my voicechannel!')

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('*??? | Disconnected.')

    @commands.command(aliases=['queue'])
    async def ListQueue(self, ctx):
        """ prints out the current song queue including the currently playing song """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.blurple())

        embed.title = "Current Queue:"
        description = ""
        
        # Adding the current track
        ct = player.current
        if ct != None:
            description += f"\n Playing: [{ct.title}]({ct.uri})"

        for song, i in enumerate(player.queue):
            description += f"\n {i}: [{song.title}]({song.uri})"

        embed.description = description
        await ctx.send(embed=embed)


    @commands.command(aliases=['volume'])
    async def ChangeVolume(self, ctx, volume: float):
        """ prints out the current song queue including the currently playing song """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.blurple())

        embed.title = "Volume updated:"
        embed.description = f"Volume updated to: {volume}"
        
        settings["guild_settings"][ctx.guild.id] = {"default_volume": volume}

        await player.set_volume(volume)
        await ctx.send(embed=embed)


    @commands.command(aliases=['skip'])
    async def SkipCurrentTrack(self, ctx):
        """ Skips the current song and plays the next one in the queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = "Song skipped!"

        # TODO: Add next in queue song name, if any
        embed.description = f"Current song skipped, playing next in queue"

        await player.skip()
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['shuffle'])
    async def ShuffleCommand(self, ctx):
        """ Skips the current song and plays the next one in the queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        bShouldShuffle = not player.shuffle


        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f"Shuffle set to {str(bShouldShuffle)}"

        # TODO: Add next in queue song name, if any
        embed.description = f"Shuffle set to {str(bShouldShuffle)} by {ctx.author.name}"

        await player.set_shuffle(bShouldShuffle)
        await ctx.send(embed=embed)


    @commands.command(aliases=['loop'])
    async def LoopCommand(self, ctx, state: int):
        """ Switches the loop setting, 0 for off, 1 for single track, 2 for queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)


        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f"Loop set to {str(state)}"

        if state == 0:
            # TODO: Add next in queue song name, if any
            embed.description = f"Loop turned off by {ctx.author.name}"
        elif state == 1:
            embed.description = f"Loop set to single track by {ctx.author.name}"
        elif state == 2:
            embed.description = f"Loop set to queue by {ctx.author.name}"
 

        await player.set_loop(state)
        await ctx.send(embed=embed)

    @commands.command(aliases=['clear'])
    async def ClearCommand(self, ctx):
        """ Skips the current song and plays the next one in the queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)


        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f"Queue cleared!"
        player.queue.clear()

        await player.skip()
        await ctx.send(embed=embed)

async def setup(bot):
   await bot.add_cog(Music(bot))