# iagon-python-bot

Telegram bot to monitor and control an Iagon node service on Ubuntu Server, with real-time alerts based on checker logs and commands for start, stop, restart, and benchmark.

## Prerequisites

- Ubuntu Server
- Iagon node installed and configured
- [iagon-checker](https://github.com/noroxi7/iagon-checker) set up and running
- `sudo` access
- Python 3 (`python3 --version` to verify)

## Telegram Setup

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions to create your bot
3. Copy the **bot token** — you will need it in the configuration step
4. To get your **chat ID**, search for **@userinfobot** in Telegram and send any message — it will reply with your ID

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/noroxi7/iagon-telegram-bot.git
cd iagon-python-bot
```

### 2. Install dependencies

Python on Ubuntu 24 is managed by the system and blocks global package installations by default. Use `--break-system-packages` to install the required library:

```bash
pip install "python-telegram-bot[job-queue]" --break-system-packages
```

This flag overrides Ubuntu's restriction and installs the package globally. It is safe for a dedicated server running a single purpose application.

### 3. Configure the bot

Edit `python-bot.py` and set the following values at the top of the file:

```python
BOT_TOKEN  = "YOUR_BOT_TOKEN"   # Token from BotFather
ALLOWED_ID = 123456789          # Your chat ID from @userinfobot
LOG_PATH   = "/home/youruser/iagon/iagon-checker/logs"  # Path to iagon-checker logs
```

### 4. Configure sudo without password

The bot runs commands with `sudo` from a non-interactive environment. You need to allow this without a password prompt.

Open the sudoers file:

```bash
sudo visudo
```

Add the following line **at the very end of the file**, after all other rules:

```
yourusername ALL=(ALL) NOPASSWD: /usr/local/bin/iagon-node
```

Replace `yourusername` with your system user. The line must be at the end because earlier rules like `%sudo ALL=(ALL:ALL) ALL` take precedence and will override it otherwise.

### 5. Run as a systemd service

Copy the service file:

```bash
sudo cp iagon-python-bot.service /etc/systemd/system/
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable iagon-python-bot
sudo systemctl start iagon-python-bot
```

Check that it is running:

```bash
systemctl status iagon-python-bot
```

## Commands

| Command | Description |
|---|---|
| /status | Check service status |
| /start_node | Start the service |
| /stop | Stop the service |
| /restart | Restart the service |
| /benchmark | Run performance benchmark |
| /logs | Show last 20 log entries |
| /help | Show available commands |

## How it works

The bot checks the iagon-checker log file every minute. If it detects a stopped service, an error, or a permission issue, it sends an alert to your Telegram with the full context block. It also responds to manual commands for controlling the node directly from Telegram.

On startup, the bot initializes its position to the current end of the log file, so it only notifies about new events and does not replay past alerts.

## License

MIT