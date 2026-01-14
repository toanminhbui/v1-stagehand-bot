"""
Main Slack bot application using Socket Mode.
Handles link verification and copy review.
"""

import asyncio
import logging
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import get_config
from .analyzer import extract_links_and_claims, summarize_claims
from .stagehand_client import StagehandClient
from .copy_reviewer import CopyReviewer, format_review_result
from .formatter import (
    format_slack_reply,
    format_error_message,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> App:
    """Create and configure the Slack Bolt application."""
    config = get_config()
    
    app = App(
        token=config.slack_bot_token,
        signing_secret=config.slack_signing_secret,
    )
    
    # Initialize clients
    stagehand_client = StagehandClient(
        api_key=config.browserbase_api_key,
        project_id=config.browserbase_project_id,
    )
    
    copy_reviewer = CopyReviewer()
    
    @app.event("app_mention")
    def handle_mention(event, say, client):
        """
        Handle when the bot is mentioned in a channel.
        Reviews the marketing copy for:
        1. Link verification (do links match their descriptions?)
        2. Spelling and wording suggestions
        """
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        message_text = event.get("text", "")
        user = event.get("user")
        
        logger.info(f"Received mention from user {user} in channel {channel}")
        
        # Remove the bot mention from the text
        cleaned_text = re.sub(r'<@[A-Z0-9]+>\s*', '', message_text).strip()
        
        if not cleaned_text:
            say(
                text="Please include some marketing copy for me to review! I'll check links and suggest improvements.",
                thread_ts=thread_ts,
            )
            return
        
        # Post initial "working on it" message
        working_msg = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="🔍 Analyzing your marketing copy...\n• Checking links\n• Reviewing spelling & wording\n\n_This may take a moment..._",
        )
        
        try:
            # Run async analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run both analyses concurrently
                link_results, copy_review = loop.run_until_complete(
                    analyze_copy(cleaned_text, stagehand_client, copy_reviewer)
                )
            finally:
                loop.close()
            
            # Build the response
            response_parts = []
            
            # Link verification results
            if link_results:
                response_parts.append(format_slack_reply(link_results))
            else:
                response_parts.append("_No links found in the copy to verify._")
            
            # Copy review results
            response_parts.append("\n" + "─" * 40 + "\n")
            response_parts.append(format_review_result(copy_review))
            
            response_text = "\n".join(response_parts)
            
            # Update the working message with results
            client.chat_update(
                channel=channel,
                ts=working_msg["ts"],
                text=response_text,
            )
            
            logger.info(f"Successfully analyzed copy with {len(link_results)} link(s)")
        
        except Exception as e:
            logger.error(f"Error analyzing copy: {e}", exc_info=True)
            
            client.chat_update(
                channel=channel,
                ts=working_msg["ts"],
                text=format_error_message(str(e)),
            )
    
    @app.event("message")
    def handle_message(event, logger):
        """Handle regular messages (no-op, we only respond to mentions)."""
        if event.get("channel_type") == "im":
            logger.debug(f"Received DM: {event.get('text', '')[:50]}")
    
    @app.error
    def handle_errors(error, body, logger):
        """Global error handler."""
        logger.error(f"Slack app error: {error}")
        logger.debug(f"Request body: {body}")
    
    return app


async def analyze_copy(text: str, stagehand_client: StagehandClient, copy_reviewer: CopyReviewer):
    """
    Analyze marketing copy - both link verification and copy review.
    Runs both analyses concurrently for speed.
    """
    # Extract links
    claims = extract_links_and_claims(text)
    logger.info(summarize_claims(claims))
    
    # Run analyses
    if claims:
        # Run both concurrently when there are links
        link_results, copy_review = await asyncio.gather(
            stagehand_client.analyze_links(claims),
            copy_reviewer.review_copy(text),
        )
    else:
        # No links, just do copy review
        link_results = []
        copy_review = await copy_reviewer.review_copy(text)
    
    return link_results, copy_review


def main():
    """Main entry point for running the bot."""
    logger.info("Starting Marketing Copy Review Bot...")
    
    try:
        config = get_config()
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables.")
        return
    
    app = create_app()
    
    # Start the Socket Mode handler
    handler = SocketModeHandler(app, config.slack_app_token)
    
    logger.info("Bot is starting in Socket Mode...")
    logger.info("Mention the bot with @BotName to review marketing copy")
    
    handler.start()


if __name__ == "__main__":
    main()
