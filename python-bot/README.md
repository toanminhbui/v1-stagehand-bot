# Marketing Copy Review Slack Bot

A Python-based Slack bot that reviews marketing materials. When mentioned, it:
1. **Verifies links** - Uses Browserbase Stagehand to check if linked pages match their descriptions
2. **Reviews copy** - Checks spelling, grammar, and suggests wording improvements using OpenAI

## Features

- **Mention-triggered**: Simply @mention the bot in any channel with marketing copy
- **Link verification**: Checks if linked pages match their descriptions (apply links, speaker profiles, etc.)
- **Copy review**: Spelling, grammar, and wording suggestions powered by OpenAI
- **Browserbase Stagehand**: AI-powered browser automation to analyze linked pages
- **Threaded responses**: Replies in-thread with detailed results

## Prerequisites

- Python 3.10+
- A Slack workspace with admin access to create apps
- Browserbase account with API credentials
- (Optional) OpenAI API key for enhanced analysis

## Slack App Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Choose "From scratch" and give it a name (e.g., "Link Verifier")
3. Select your workspace

### Enable Socket Mode

1. Go to **Socket Mode** in the sidebar
2. Enable Socket Mode
3. Create an App-Level Token with `connections:write` scope
4. Save the token as `SLACK_APP_TOKEN`

### Configure OAuth & Permissions

1. Go to **OAuth & Permissions**
2. Add these Bot Token Scopes:
   - `app_mentions:read` - To receive mention events
   - `chat:write` - To reply in channels
   - `channels:history` - To read channel messages
   - `groups:history` - To read private channel messages (optional)
3. Install the app to your workspace
4. Save the Bot User OAuth Token as `SLACK_BOT_TOKEN`

### Enable Event Subscriptions

1. Go to **Event Subscriptions**
2. Enable events
3. Subscribe to bot events:
   - `app_mention`
4. Save changes

### Get Signing Secret

1. Go to **Basic Information**
2. Find the Signing Secret
3. Save it as `SLACK_SIGNING_SECRET`

## Installation

1. Clone the repository and navigate to the python-bot directory:

```bash
cd python-bot
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the example environment file and fill in your credentials:

```bash
cp env.example .env
```

5. Edit `.env` with your actual credentials:

```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-level-token
BROWSERBASE_API_KEY=your-browserbase-api-key
BROWSERBASE_PROJECT_ID=your-project-id
OPENAI_API_KEY=your-openai-api-key  # Optional
```

## Running the Bot

### Local Development (Socket Mode)

```bash
python -m bot.app
```

The bot will connect via WebSocket and start listening for mentions.

### Deploy to Railway

1. **Push code to GitHub**

2. **Create Railway project:**
   - Go to [railway.app](https://railway.app)
   - New Project → Deploy from GitHub repo
   - Select your repo
   - Set Root Directory to `python-bot`

3. **Add environment variables in Railway:**
   ```
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_SIGNING_SECRET=your-secret
   SLACK_APP_TOKEN=xapp-your-app-token
   BROWSERBASE_API_KEY=your-browserbase-key
   BROWSERBASE_PROJECT_ID=your-project-id
   MODEL_API_KEY=your-openai-key
   ```

4. **Deploy** - Railway auto-detects Python and runs the Procfile

The bot uses Socket Mode, so no public URL is needed - it connects outbound to Slack.

## Usage

Once the bot is running and installed in your workspace:

1. Invite the bot to a channel: `/invite @LinkVerifier`
2. Mention the bot with marketing copy containing links:

```
@LinkVerifier Please review this:

We're hiring! Apply now: https://careers.example.com/apply

Meet our speakers:
- Jane Doe: https://linkedin.com/in/janedoe
- John Smith: https://example.com/team/john
```

3. The bot will reply in a thread with verification results for each link.

## Example Output

```
📋 Link Verification Results

3 links checked: 2 aligned, 1 needs review

*Link 1:* `https://careers.example.com/apply`
✅ *Aligned* – Page is an application form titled "Join Our Team"

*Link 2:* `https://linkedin.com/in/janedoe`
✅ *Aligned* – LinkedIn profile for Jane Doe, matches expected speaker

*Link 3:* `https://example.com/team/john`
⚠️ *Questionable* – Page is a team directory, not a specific profile for John Smith

────────────────────────────────────────

📝 Copy Review Results

🌟 *Overall Score: 92/100*
_The copy is clear and engaging._

✍️ Wording Suggestions (1):
  💡 "Join our team"
     → "Join our growing team"
     _Reason: More engaging and implies momentum_
```

## Development

### Project Structure

```
python-bot/
├── bot/
│   ├── __init__.py
│   ├── app.py              # Main Slack bot application
│   ├── analyzer.py         # Message parsing and claim extraction
│   ├── config.py           # Configuration management
│   ├── formatter.py        # Slack response formatting
│   ├── models.py           # Data models
│   └── stagehand_client.py # Browserbase Stagehand integration
├── env.example
├── requirements.txt
└── README.md
```

### Running Tests

```bash
pytest tests/
```

## Troubleshooting

### Bot doesn't respond to mentions

1. Check that the bot is invited to the channel
2. Verify `app_mention` event subscription is enabled
3. Check the console for error messages
4. Ensure all environment variables are set correctly

### Stagehand analysis fails

1. Verify your Browserbase API key and project ID
2. Check that you have available browser sessions in your Browserbase account
3. Some pages may block automated browsers - check the error details

## License

MIT

