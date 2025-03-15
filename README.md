# MCP Telegram Bot

Telegram bot with support for various LLM models and Model Context Protocol client

## Installation

1. Clone the repository
```bash
git clone <repository-url>
```

2. Create a virtual environment and activate it
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example` and add your bot token

5. Run the bot
```bash
python main.py
```

## Commands

- `/start` - Start chatting with the bot
- `/model` - Select a model
- `/client` - Select a client api