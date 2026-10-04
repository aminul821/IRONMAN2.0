<p align="center">
  <img src="https://telegra.ph/file/5ebc8dc898b2f6afcc34c.jpg">
</p>

# IRONMAN2.0

A Telegram group management bot: admin tools, warns, notes, filters, welcome
messages, federations, anti-flood, blacklists, locks, NSFW guard, music
downloads, an AI chatbot and lots of fun/utility commands.

## Requirements

* Python 3.11
* A PostgreSQL database (the only database needed)
* A bot token from [@BotFather](https://t.me/BotFather)
* `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
* `ffmpeg` and [Deno](https://deno.com) for `/song` and `/video` (both are in the Docker image)

## Deploy

### Heroku

<p align="center"><a href="https://heroku.com/deploy?template=https://github.com/aminul821/IRONMAN2.0"> <img src="https://img.shields.io/badge/Deploy%20To%20Heroku-black?style=for-the-badge&logo=heroku" width="220" height="38.45"/></a></p>

The app is built from the `Dockerfile` (container stack) and gets a Postgres
add-on automatically. Turn the `worker` dyno on after the build.

### Docker / VPS

```bash
git clone https://github.com/aminul821/IRONMAN2.0 && cd IRONMAN2.0
docker build -t ironman .
docker run -d --name ironman --restart unless-stopped \
  -e ENV=1 -e TOKEN=... -e API_ID=... -e API_HASH=... -e OWNER_ID=... \
  -e DATABASE_URL=postgresql://user:password@host:5432/ironman \
  ironman
```

### Without Docker

```bash
python3.11 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
export ENV=1 TOKEN=... API_ID=... API_HASH=... OWNER_ID=... DATABASE_URL=...
python3 -m IronRobo
```

Instead of environment variables you can copy `IronRobo/sample_config.py` to
`IronRobo/config.py`, fill it in and leave `ENV` unset.

## Configuration

| Variable | Required | What it does |
| --- | --- | --- |
| `ENV` | yes | Set to anything to read the settings from environment variables |
| `TOKEN` | yes | Bot token |
| `API_ID`, `API_HASH` | yes | From my.telegram.org |
| `OWNER_ID` | yes | Your Telegram user id |
| `DATABASE_URL` | yes | PostgreSQL URL (`postgres://` URLs work too) |
| `SUPPORT_CHAT` | no | Username of your support group, without `@` |
| `EVENT_LOGS` | no | Chat id for gban/sudo/error logs (bot must be admin there) |
| `JOIN_LOGGER` | no | Chat id where new groups are logged |
| `DEV_USERS`, `DRAGONS`, `DEMONS`, `TIGERS`, `WOLVES` | no | Space separated user ids for the bot's permission levels |
| `AI_API_KEY` | no | Anthropic API key, enables the chatbot (`/chatbot on`) |
| `AI_MODEL` | no | Claude model for the chatbot, default `claude-opus-5-5` |
| `OPENWEATHERMAP_ID` | no | OpenWeatherMap key for `/weather` (wttr.in is used without it) |
| `CASH_API_KEY` | no | Alpha Vantage key for `/cash` (free daily rates are used without it) |
| `GENIUS_API_TOKEN` | no | Better `/lyrics` results |
| `SPAMWATCH_API` | no | SpamWatch token for automatic spammer bans |
| `YT_COOKIES_FILE` | no | Path to a YouTube `cookies.txt`, if YouTube asks the server to sign in |
| `HEROKU_API_KEY`, `HEROKU_APP_NAME` | no | Owner commands to manage Heroku config vars |
| `STRICT_GBAN`, `ALLOW_EXCL`, `DEL_CMDS` | no | `True`/`False` switches |
| `NO_LOAD` | no | Space separated modules to skip |
| `BL_CHATS` | no | Space separated chat ids the bot leaves |

Send `/help` to the bot in private to see every module and its commands.
Apart from the chatbot (which needs `AI_API_KEY`), every feature works without
extra API keys.
