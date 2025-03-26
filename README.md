# telegram-bot

Telegram bots for Samantha's Group

## For developers

1. Clone this repository
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
3. Run `uv sync` in the project directory to [install dependencies](https://docs.astral.sh/uv/reference/cli/#uv-sync)
4. Copy [the sample .env file](sample.env) to `.env` and change all the data accordingly.
5. Install pre-commit hooks: `uv run pre-commit install`. They will run on files being committed. `black` and `isort` will fix the issues automatically. To check all code, run `uv run pre-commit run -a`.
6. Run tests: `uv run pytest`
7. Run the bot: `uv run python samanthas_telegram_bot/main.py`
