from functools import wraps
import dotenv
import nest_asyncio
import os
import time
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

nest_asyncio.apply()
dotenv.load_dotenv()

from telegram.helpers import escape, escape_markdown

from playwright.sync_api import sync_playwright
import logging

import datetime
import snscrape.modules.twitter as sntwitter

if os.environ.get("TELEGRAM_USER_ID"):
    USER_ID = int(os.environ.get("TELEGRAM_USER_ID"))


from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

# Enable logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

PLAY = sync_playwright().start()
BROWSER = PLAY.chromium.launch_persistent_context(
    user_data_dir="/tmp/playwright",
    headless=False,
)
PAGE = BROWSER.new_page()


def get_input_box():
    """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
    return PAGE.query_selector("textarea")


def is_logged_in():
    # See if we have a textarea with data-id="root"
    return get_input_box() is not None


def send_message(message):
    # Send the message
    box = get_input_box()
    box.click()
    box.fill(message)
    box.press("Enter")


class AtrributeError:
    pass


def get_last_message():
    """Get the latest message"""
    page_elements = PAGE.query_selector_all("div[class*='request-']")
    last_element = page_elements[-1]
    prose = last_element
    try:
        code_blocks = prose.query_selector_all("pre")
    except Exception as e:
        response = "Server probably disconnected, try running /reload"
        return response

    if len(code_blocks) > 0:
        # get all children of prose and add them one by one to respons
        response = ""
        for child in prose.query_selector_all("p,pre"):
            # print(child.get_property("tagName"))
            if str(child.get_property("tagName")) == "PRE":
                code_container = child.query_selector("code")
                response += f"\n```\n{escape_markdown(code_container.inner_text(), version=2)}\n```"
            else:
                # replace all <code>x</code> things with `x`
                text = child.inner_html()
                response += escape_markdown(text, version=2)
        response = response.replace("<code\>", "`")
        response = response.replace("</code\>", "`")
    else:
        response = escape_markdown(prose.inner_text(), version=2)
    return response


async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    print(f"Got a reload command from user {update.effective_user.id}")
    PAGE.reload()
    await update.message.reply_text("Reloaded the browser!")
    await update.message.reply_text("Let's check if it's working!")


# Daily list of tweets, to avoid sending the same tweet twice
tweets = []

# Create the Application and pass it your bot's token.
application = Application.builder().token(os.environ.get("TELEGRAM_API_KEY")).build()


async def search_tweets(query, update, context):
    """Search for tweets containing the specified query and send a notification for each new tweet"""
    found_tweets = []
    # Use the snscrape package to search for tweets containing the specified query
    for tweet in sntwitter.TwitterSearchScraper(query).get_items():
        found_tweets.append(tweet)

    # Set the initial retry delay to 10 seconds
    retry_delay = 10

    # Send a notification for each new tweet
    for i, tweet in enumerate(reversed(found_tweets)):
        if tweet.id not in tweets:
            # Check if gpt-chat considers the tweet worthy of a notification
            gptchat_response = await gptchat_notification_verifier(
                tweet, update, context
            )

            # Loop until the request succeeds or the maximum number of retries is reached
            while True:
                try:
                    # Send the notification if gpt-chat considers the tweet worthy
                    if gptchat_response:
                        await send_notification(tweet, gptchat_response)

                    # If the request succeeds, break out of the loop
                    break
                except telegram.error.RetryAfter as error:
                    # If the request fails with a rate limiting error, wait for the specified amount of time
                    # (The RetryAfter error contains the amount of time to wait before retrying the request)
                    time.sleep(error.retry_after)

                    # Increase the retry delay using an exponential backoff strategy
                    # (For example, double the retry delay each time the request fails)
                    retry_delay *= 2
                except:
                    # If the request fails for any other reason, break out of the loop
                    break

            # Wait 60 seconds after sending 20 notifications (To avoid hitting the Telegram Bot API rate limit - and Spam)
            if i % 20 == 0:
                time.sleep(90)
        tweets.append(tweet.id)


async def check_loading(update):
    # Set the initial retry delay to 1 second
    retry_delay = 8

    # button has an svg of submit, if it's not there, it's likely that the three dots are showing an animation
    submit_button = PAGE.query_selector_all("textarea+button")[0]
    # with a timeout of 90 seconds, created a while loop that checks if loading is done
    loading = submit_button.query_selector_all(".text-2xl")

    # Loop until the request succeeds or the maximum number of retries is reached
    while True:
        try:
            # keep checking len(loading) until it's empty or 45 seconds have passed
            await application.bot.send_chat_action(update.effective_chat.id, "typing")
            start_time = time.time()
            while len(loading) > 0:
                if time.time() - start_time > 90:
                    break
                time.sleep(0.5)
                loading = submit_button.query_selector_all(".text-2xl")
                await application.bot.send_chat_action(
                    update.effective_chat.id, "typing"
                )

            # If the request succeeds, break out of the loop
            break
        except telegram.error.RetryAfter as error:
            # If the request fails with a rate limiting error, wait for the specified amount of time
            # (The RetryAfter error contains the amount of time to wait before retrying the request)
            time.sleep(error.retry_after)

            # Increase the retry delay using an exponential backoff strategy
            # (For example, double the retry delay each time the request fails)
            retry_delay *= 2


async def gptchat_notification_verifier(tweet, update: Update, context) -> None:
    """Filter the tweet with GPT-Chat. Ask GPT-Chat to tell us if the tweet is worth notifying the user about."""
    prompt = f"""
    Lets play a game. You have been hired to spend all day reading tweets about gptchat and openAI. Your job is to make a selection of the most important, relevant or interesting tweets to your boss.
    Your boss is interested in: technical aspects of the technology (e.g. In-depth Topics revolving AI suited for technical people like LLMs, training gpt-3, etc), the impact of the technology on society, new use cases of the technology (e.g. using it as a business consultant or startup advisor), new tools built with it like programs and chrome extensions, new startup ideas, etc.
    He already knows about the creation of gptchat and knows what any non-technical person knows about it, so ignore all the tweets that intend to inform people about the release of the technology. The gptchat hype is real all over social media, so everyone is talking about it. Unless the tweet is worth notifying your boss about, don't do so.
    You have to decide which tweets are worth notifying him about. He does not want to waste his time reading tweets that do not contribute to his work or interests. He already knows about the creation of gptchat and knows what any non-technical person knows about it, so ignore all the tweets that intend to inform people about the release of the technology. The gptchat hype is real all over social media,
    so everyone is talking about it. Unless the tweet is worth notifying your boss about, don't do so.

    Answer with
    X 
    Y
    where X is "YES" or "NO" and Y is the reason you think it is important, relevant or interesting to your boss. YES if the tweet is worth notifying your boss about, NO if it is not. I want you to only reply with X (YES or NO) and Y (The reason why you thought it was worth notifying). Do not write anything more. \n

    Below are 4 different prompt examples and your answers, 2 of a worth sharing tweet and another 2 of a not worth sharing tweet.
    
    Example 1 of prompt of a tweet worth sharing: 
    Tweet: We may see GPT-Chat replacing many trivial classification NN models in the near future. Here is why...
    Answer
    YES
    Contains interesting information regarding the future replacement of NN models with Large Language Models like GPT-Chat.

    Example 2 of prompt of a tweet worth sharing:
    Tweet: A new education startup in California aims to be powered by GPT-Chat. Click on the article to read more about it! ...
    Answer
    YES
    Contains interesting information regarding the future of education powered by GPT-Chat.

    Example 1 of prompt of a tweet not worth sharing:
    Tweet: gptchat is a great tool for generating text. I just told it to make my homework for me and it did it better than I ever would.
    Answer
    NO
    Contains no important, relevant or interesting information regarding GPT-Chat or OpenAI. 

    Example 2 of prompt of a tweet not worth sharing:
    Tweet: Introducing ChatGPT, the new, powerful AI-powered language model from OpenAI! \n
    Answer
    NO
    Contains no important, relevant or interesting information regarding GPT-Chat or OpenAI since the boss already knows about it. 

    The game starts now and below is the first tweet that you have to decide if it is worth notifying your boss about or not. 
    
    Tweet: {tweet.content}
    """
    send_message(prompt)
    await check_loading(update)
    response = get_last_message()
    if response[:3] == "YES":
        return response[3:]
    elif response[:2] == "NO":
        return None
    else:
        print(
            "Invalid GPT-Chat response. Probably too many requests on ChatGPT. Waiting 5 minutes and trying again."
        )
        # It is likely that too many requests have been sent to ChatGPT, with the "Too many requests, please slow down" error message
        time.sleep(60 * 5)
        reload(update, context)
        while response[:3] != "YES" or response[:2] != "NO":
            await gptchat_notification_verifier(tweet, update, context)


async def send_notification(tweet, gptchat_response):
    """Send a notification about the specified tweet to the specified user"""
    # Use the python-telegram-bot package to send a notification to the specified user
    bot = telegram.Bot(token=os.environ.get("TELEGRAM_API_KEY"))

    # Send a notification to the specified user
    await bot.send_message(
        int(os.environ.get("TELEGRAM_USER_ID")),
        text=f"<b>GPT-Chat Judgement:</b> {gptchat_response} \n ------------------------------------ \n <b>Date</b>: {tweet.date.strftime('%Y-%m-%d %H:%M')} \n ------------------------------------ \n <b>Content</b> \n{tweet.content} \n ------------------------------------ \n <b>Url:</b> \n{tweet.url}",
        parse_mode=telegram.constants.ParseMode.HTML,
    )


# function to change the date on the query every new day
def change_date():
    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d")
    query = "gptchat OR chatgpt OR chat-gpt OR gpt-chat openAI lang:en since:" + date
    return query


async def start(update: Update, context: ContextTypes):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        f"Hi! I am your smart <b>GPT-Chat & OpenAI</b> bot that sends you notifications for every new tweet containing the words <b> GPT-Chat </b> or <b> openAI </b> (or any other variants of the same words) accounting for punctuations and case sensitivity. The notifications should include: \n - <b> The reason why GPT-Chat deemed the tweet worth sending a notification  \n - The date of the tweet  \n - The full content of the tweet  \n - Url of the tweet </b>  \n \n <b> NOTE: </b> To not bombard you with stupidity, I will filter the new tweets (using GPT-Chat itself) and only send you the ones that you might actually find interesting :)",
        parse_mode=telegram.constants.ParseMode.HTML,
    )
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    query = "gptchat OR chatgpt OR chat-gpt OR gpt-chat openAI lang:en since:" + date
    running = True
    while running:
        query = current_date(query)
        await search_tweets(query, update, context)
        # Wait 1 minute before searching for new tweets
        time.sleep(60)


def current_date(query):
    """Check if the current date is the same as the date in the query, if not change the date in the query"""
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    if query[-10:] != date:
        tweets = []
        updated_query_date = (
            "gptchat OR chatgpt OR chat-gpt OR gpt-chat openAI lang:en since:" + date
        )
        return updated_query_date
    else:
        return query


async def help(update: Update, context: ContextTypes):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Use /start to get started, and /stop to stop the bot from sending notifications."
    )


async def stop(update: Update, context: ContextTypes):
    """Send a message when the command /stop is issued."""
    await update.message.reply_text("The bot will stop sending notifications.")

    # Stop the loop that searches for tweets and sends notifications
    global running
    running = False


def start_browser():
    PAGE.goto("https://chat.openai.com/")
    if not is_logged_in():
        print("Please log in to OpenAI Chat")
        print("Press enter when you're done")
        input()
    else:
        # on different commands - answer in Telegram
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("reload", reload))
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("stop", stop))

        # Run the bot until the user presses Ctrl-C
        application.run_polling()


if __name__ == "__main__":
    start_browser()
