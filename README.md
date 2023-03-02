# discord-music-py
Python bot for streaming music to discord via lavalink 

In order to run this you'll need to have a version of **JRE** _lord save our souls_ and create a few files. I've included an `application.yml` which should outline how the Lavalink.jar app should function.

You can get the lavalink jre [here](https://github.com/freyacodes/Lavalink/releases/) -- This should live in the same root folder as this repo (Where `application.yml` lives)
It can be run with a simple command like: `java -jar Lavalink.jre`

You'll also need to create two things: a spotify developer application, which can be done [here](https://developer.spotify.com/dashboard/login) -- You'll need your client_id and your client_secret
Place those into a `spotify_secrets.json` file alongside your `settings.json` file. I'll include some example json for this purpose:

```
{
    "client_id": "xxxxxxxxxxxxxxxxxxxxxx",
    "secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

As well, you'll need a discord bot and it's token, the token can just be slapped into a txt file called `token.txt` for now -- In the future i'd be preferable to load this through env var as well

Once that's finished and you've added the bot, you should only need to run `python ./discordmusic.py`
