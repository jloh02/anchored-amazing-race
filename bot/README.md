# Anchored Amazing Race Bot

## Setup

### Third Party Access

Ensure the project owner grants access to the following:

- Firebase Project
- `credentials.json` for Firebase access to bot (Do **NOT** lose or share this key and let the owner know if it get leaked)

### Telegram Bot Setup

You should use your own bot for local testing

- Search for @BotFather on Telegram
- Follow the steps to create your own bot
- Copy the token (Keep this a secret)

### Local Dev Environment Setup

#### Step 1: Clone GitHub Repository

```
git clone https://github.com/jloh02/anchored-amazing-race
cd bot
```

#### Step 2: Setting up credentials

- Copy `credentials.json` into the `bot/` directory
- Copy the following into `bot/.env` (Remember to change the Telegram bot key from the previous steps)

```
SERVICE_ACCOUNT_PATH="./credentials.json"
TELEGRAM_BOT_KEY="<TELEGRAM_BOT_KEY>"
```

#### Step 3: Install Dependencies

```
pip install -r requirements.txt
```

#### Step 4: Run Bot

```
python main.py
```
