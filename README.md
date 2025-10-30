# Imoova Better Notifier 🚐

A Python script that monitors [Imoova.com](https://www.imoova.com) for campervan/RV relocation deals and sends notifications via Telegram when new offers matching your criteria are found.

## Features ✨

- Scrapes Imoova's European relocation deals in real-time
- Filters offers by origin and destination cities
- Sends notifications via Telegram with offer details
- Tracks seen offers to avoid duplicate notifications
- Weekly "still alive" messages to confirm the bot is running
- Supports both configuration file and environment variables
- Handles accented characters in city names

## Prerequisites 📋

- Python 3.x
- A Telegram bot token (get one from [@BotFather](https://t.me/botfather))
- Your Telegram chat ID(s)

## Installation 🔧

1. Clone this repository:
```bash
git clone https://github.com/onofrebg/imoova-better-notifier.git
cd imoova-better-notifier
```

2. Install required packages:
```bash
pip install requests beautifulsoup4
```

3. Create your configuration file:
```bash
cp config.example.json config.json
```

4. Edit `config.json` with your settings:
```json
{
    "telegram_token": "YOUR_BOT_TOKEN_HERE",
    "telegram_chats": ["YOUR_CHAT_ID_HERE"],
    "default_cities": ["Madrid", "Barcelona", "Paris"]
}
```

## Usage 🚀

### Basic Usage

Run the script with default configuration:
```bash
python main.py
```

### Command Line Options

- `--config`: Path to configuration file (default: `config.json`)
- `--cities`: Comma-separated list of cities to filter by (e.g., `Madrid,Barcelona,Zurich`)
- `--telegram-token`: Telegram bot token
- `--telegram-chats`: Comma-separated list of Telegram chat IDs
- `--seen-file`: Path to seen offers JSON file (default: `seen_offers.json`)

Example with command line options:
```bash
python main.py --cities "Madrid,Barcelona" --telegram-token "YOUR_TOKEN" --telegram-chats "CHAT_ID1,CHAT_ID2"
```

### Environment Variables

You can also configure the script using environment variables:
- `TELEGRAM_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHATS`: Comma-separated list of chat IDs
- `DEFAULT_CITIES`: Comma-separated list of cities to monitor
- `CONFIG_FILE`: Path to configuration file

## Notification Format 📬

Notifications are sent via Telegram with the following format:
```
✨ Origin -> Destination
Start Date - End Date
Vehicle Model
Duration: X days
[Link to offer]
```

## Features in Detail 🔍

### City Matching
- Case-insensitive matching
- Handles accented characters (e.g., "Zürich" matches "zurich")
- Substring matching for flexibility

### Offer Tracking
- Maintains a list of seen offers to prevent duplicate notifications
- Automatically prunes stale offers that no longer exist on the site
- Saves offer IDs to `seen_offers.json`

### Error Handling
- Robust error handling for network issues
- Notifications for script errors via Telegram
- Automatic retry mechanisms

### Alive Messages
- Sends weekly "still alive" messages when no new offers are found
- Helps confirm the bot is still running and monitoring

## Disclaimer ⚠️

This project is not affiliated with Imoova.com. Use responsibly and in accordance with Imoova's terms of service.
