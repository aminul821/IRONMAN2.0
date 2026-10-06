<p align="center">
  <img src="https://telegra.ph/file/5ebc8dc898b2f6afcc34c.jpg">
</p>

# IRONMAN2.0

A Telegram group management bot: admin tools, warns, notes, filters, welcome
messages, federations, anti-flood, blacklists, locks, NSFW guard, music
downloads, an AI chatbot and lots of fun/utility commands. Groups can be moved
over from Rose with one command.

## Features

* **Moderation:** ban, mute, kick, warn, purge, anti-flood, blacklists, locks,
  approvals, reports, federations, global bans, zombie cleanup
* **Group content:** notes, filters (text, stickers, GIFs, photos, videos,
  voice notes), welcome/goodbye messages, rules, disabled commands
* **Protection:** NSFW guard (runs locally), profanity filter, English-only
  mode, force-subscribe to a channel, night mode
* **Extras:** `/song`, `/video` and `/lyrics`, `/google`, `/img`, `/wall`,
  `/imdb`, `/app`, `/weather`, `/time`, `/cash`, `/tr`, `/tts`, `/math`,
  `/paste`, sticker kanging, logos, karma, an AI chatbot and more

Send `/help` to the bot in private to see every module and its commands.

## Requirements

* Python 3.11 (the Docker image already has it)
* A PostgreSQL database, the only database needed (see below for a free one)
* A bot token from [@BotFather](https://t.me/BotFather)
* `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
* `ffmpeg` and [Deno](https://deno.com) for `/song` and `/video` (both are in the Docker image)

### A free PostgreSQL database

1. Sign up at [neon.tech](https://neon.tech) and create a project. Pick the
   region **closest to where the bot runs**: every database query travels
   there and back, so a far-away region makes the bot slower.
2. Copy the connection string Neon shows under **Connect**, e.g.
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`
3. Use it as `DATABASE_URL`. The bot creates its tables on the first start.

Keep the connection string private: it contains your database password.

## Deploy

### Docker (recommended, works on any Linux incl. Kali)

```bash
sudo apt update && sudo apt install -y docker.io git
sudo systemctl enable --now docker

git clone https://github.com/aminul821/IRONMAN2.0 && cd IRONMAN2.0
sudo docker build -t ironman .

sudo docker run -d --name ironman --restart unless-stopped \
  -e ENV=1 \
  -e TOKEN="123456:your-bot-token" \
  -e API_ID="1234567" \
  -e API_HASH="your-api-hash" \
  -e OWNER_ID="your-telegram-user-id" \
  -e DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require" \
  ironman

sudo docker logs -f ironman
```

Keep the double quotes around every value: database URLs often contain `&`,
which the shell would otherwise cut off. The bot is running when the log says
`Using long polling.`; send it `/start` to check.

### Update to the latest version

```bash
cd IRONMAN2.0 && git pull
sudo docker build -t ironman .
sudo docker rm -f ironman
```

Then start it again with the same `docker run` command. Your data lives in the
database, so nothing is lost.

### Heroku

<p align="center"><a href="https://heroku.com/deploy?template=https://github.com/aminul821/IRONMAN2.0"> <img src="https://img.shields.io/badge/Deploy%20To%20Heroku-black?style=for-the-badge&logo=heroku" width="220" height="38.45"/></a></p>

The app is built from the `Dockerfile` (container stack) and gets a Postgres
add-on automatically. Turn the `worker` dyno on after the build.

### Without Docker

Needs Python 3.11 exactly (python-telegram-bot 13 doesn't run on 3.13).

```bash
python3.11 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
export ENV=1 TOKEN=... API_ID=... API_HASH=... OWNER_ID=... DATABASE_URL="..."
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
| `ALLOWED_GROUPS` | no | Lock the bot to these group ids; groups the owner adds it to are allowed automatically, it leaves any other group |

Apart from the chatbot (which needs `AI_API_KEY`), every feature works without
extra API keys.

## Log channel

Like Rose, every group can send its moderation log to a channel:

1. Add the bot to your channel as an admin (it needs to post messages).
2. In the group, send `/setlog <channel id or @username>`. Or post `/setlog`
   in the channel and forward that message to the group.

`/logchannel` shows the current channel, `/unsetlog` stops logging.
`/logcategories` lists what gets logged; turn categories on or off with
`/log <category>` and `/nolog <category>` (or `all`):

| Category | Logs |
| --- | --- |
| `settings` | Filters, notes, rules, locks, anti-flood, welcome, warn limit, blocklist changes |
| `admin` | Bans, mutes, kicks, warns, promotions, approvals, pins, purges |
| `user` | Members joining and leaving |
| `automated` | Actions the bot takes on its own: anti-flood, blocklist, warn filters |
| `reports` | `/report` and `@admin` |

If the bot is removed from the channel, logging is turned off and the group is told.

## Moving a group from Rose

1. Send `/export` in the group while [@MissRose_bot](https://t.me/MissRose_bot) is there.
2. Reply to the file Rose sends with `/importrose` (group admins only).

Filters, notes, rules, the blocklist, anti-flood, warn settings,
welcome/goodbye, locks, disabled commands and the report setting are copied.
Filters or notes whose sticker/media the bot can't reuse are listed by name so
you can add them again by replying to the media with `/filter <name>`.
Per-user warn counts and federation bans are not part of Rose's export.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `msg_id is too low` / `client time has to be synchronized` | Sync the clock: `sudo timedatectl set-ntp true` (under WSL: `sudo hwclock -s`) |
| Startup or commands are slow | The database is far away; create the Neon project in a region near the server |
| `/song` fails with "sign in to confirm you're not a bot" | Export YouTube cookies to `cookies.txt`, mount it (`-v /path/cookies.txt:/app/cookies.txt`) and set `YT_COOKIES_FILE=/app/cookies.txt` |
| `/tr` says Google Translate is busy | Google rate-limits busy servers; it pauses 10 minutes and recovers. `/globalmode off` (English-only mode) reduces the load |
| The chatbot doesn't answer | Set `AI_API_KEY` and turn it on in the group with `/chatbot on` |

To see what the bot is doing: `sudo docker logs --tail 50 ironman`.
