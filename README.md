# GPT-Chat Telegram Bot for important/relevant Tweets - @vinccirom

**NOTICE:** This bot is intended for those who want to be informed about any relevant tweets containing any given set of words that fulfill your personal interests. By default, it's primary use is to notify mostly technical and interested users about GPT-Chat's underlying technology and it's effects. However, this can be ammended to utilize other words and other interests.

This is a telegram bot written in python that sends you filtered notifications for every new tweet containing the words  GPT-Chat  or  openAI  (or any other variants of the same words) accounting for punctuations and case sensitivity. The tweets are filtered by GPT-Chat, meaning that the notifcations that you will receive are classified as important, interesting or relevant to you by GPT-Chat, therefore removing most of the noise given the current hype (with over 1.200 related tweets daily to today's date).

![example_tweet](https://user-images.githubusercontent.com/49160592/206353131-d2b03783-da00-4285-aed3-8443586a9d94.png)

## Features & Commands
* Receive filtered notifications about tweets containing the words 'GPT-Chat', 'Chat-GPT', 'GPTChat', ChatGPT', 'openAI' (case-punctuation insensitive)
* `/start` To start the bot and receive notifications
* `/reload` To reload in the case that the server disconnects
* `/help` To view commands
* `/stop` To stop receiving notifications

![starting_bot](https://user-images.githubusercontent.com/49160592/206346970-44c43ae3-26b6-4571-9ed7-6c9da2ac9aa9.png)

The conditions that determine whether GPT-Chat classifies the tweet as important, interesting or relevant can be ammended by changing the prompt inside the `gptchat_notification_verifier` function. Currently, it assumes that you are interested in:

-----------------------------------------------------------------------------------------------------------------------------
> Technical aspects of the technology (e.g. In-depth Topics revolving AI suited for technical people like LLMs, training gpt-3, etc), the impact of the technology on society, new use cases of the technology (e.g. using it as a business consultant or startup advisor), new tools built with it like programs and chrome extensions, new startup ideas, etc. You already know about the creation of gptchat and knows what any non-technical person knows about it, so ignore all the tweets that intend to inform people about the release of the technology. Ignore all the tweets that intend to inform people about the release of the technology.
-----------------------------------------------------------------------------------------------------------------------------

## How to install ##
1. Install Python and the Conda package manager (Instructions for installing Python and Conda can be found [here](https://www.python.org/ and https://docs.conda.io/en/latest/)).

2. Create a new Conda environment and activate it (Instructions for creating and activating a Conda environment can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)).

3. Install the required Python packages (using `pip install`): 
  - `snscrape`
  - `python-telegram-bot`
  - `python-dotenv` 
  - `requests` 
  - `nest-asyncio`

(Instructions for installing Python packages with pip can be found [here](https://pip.pypa.io/en/stable/quickstart/))

4. Install Playwright in your Conda environment. 
`playwright install`

5. Run the playwright install-deps command to download the necessary dependencies. 
`playwright install-deps`

6. Set up the Telegram bot token and user ID in the .env file (Instructions for setting up the Telegram bot token and user ID can be found [here](https://core.telegram.org/bots#botfather)).

7. Edit the `.env.example` file, rename it to `.env`, and place your values in the appropriate fields.

8. Open a terminal or command prompt and navigate to the directory where the bot was installed (Make sure the .env file and bot.py file are in the same directory).

9. Run python bot.py to start the server.

10. Open the Telegram app on your device.

11. Find the bot in the list of contacts (you should have already created it with @BotFather).

12. Type the command `/start` to start the bot.
