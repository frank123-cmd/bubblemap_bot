# bot/bot.py
import os
import django
import requests
from django.db import models
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.ext import ContextTypes
from telegram.error import TimedOut
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
from dotenv import load_dotenv
from collections import defaultdict
from asgiref.sync import sync_to_async  # For async ORM queries
import asyncio

# Load environment variables from .env file
load_dotenv()

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bot.settings')
django.setup()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Django model for caching token data
class TokenData(models.Model):
    contract_address = models.CharField(max_length=100, unique=True)
    chain = models.CharField(max_length=10)
    market_cap = models.FloatField(null=True)
    price = models.FloatField(null=True)
    volume = models.FloatField(null=True)
    decentralization_score = models.FloatField(null=True)
    percent_in_cexs = models.FloatField(null=True)
    percent_in_contracts = models.FloatField(null=True)
    top_traders = models.JSONField(null=True)  # Store top traders as JSON
    trader_connections = models.JSONField(null=True)  # Store connections as JSON

    class Meta:
        app_label = 'bot'

# Bot token and API configurations from .env
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env file. Please set it.")

BUBBLEMAPS_API_URL = os.getenv('BUBBLEMAPS_API_URL')
BUBBLEMAPS_API_KEY = os.getenv('BUBBLEMAPS_API_KEY')
SCORE_API_URL = os.getenv('SCORE_API_URL')
SCORE_API_KEY = os.getenv('SCORE_API_KEY')

if not (BUBBLEMAPS_API_URL and SCORE_API_URL):
    raise ValueError("Missing API URLs in .env file. Please set BUBBLEMAPS_API_URL and SCORE_API_URL.")

COINGECKO_COINS_LIST_URL = "https://api.coingecko.com/api/v3/coins/list?include_platform=true"
COINGECKO_COIN_DATA_URL = "https://api.coingecko.com/api/v3/coins/{}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"

# Cache for CoinGecko coin list to avoid repeated API calls
COINGECKO_COIN_MAPPING = None

# Function to map contract address to CoinGecko coin_id
def get_coingecko_coin_id(contract_address, chain):
    global COINGECKO_COIN_MAPPING
    try:
        if COINGECKO_COIN_MAPPING is None:
            response = requests.get(COINGECKO_COINS_LIST_URL)
            if response.status_code != 200:
                logger.error(f"CoinGecko coins list API error: {response.status_code}")
                return None
            COINGECKO_COIN_MAPPING = response.json()

        # Map chain to CoinGecko platform
        chain_mapping = {
            'eth': 'ethereum',
            'bsc': 'binance-smart-chain',
            'ftm': 'fantom',
            'avax': 'avalanche',
            'cro': 'cronos',
            'arbi': 'arbitrum',
            'poly': 'polygon-pos',
            'base': 'base',
            'sol': 'solana',
            'sonic': 'sonic'  # Assuming CoinGecko supports this chain
        }
        platform = chain_mapping.get(chain)
        if not platform:
            logger.error(f"Unsupported chain: {chain}")
            return None

        # Find the coin with the matching contract address
        for coin in COINGECKO_COIN_MAPPING:
            platforms = coin.get('platforms', {})
            if platforms.get(platform) == contract_address:
                return coin['id']
        logger.error(f"No CoinGecko coin found for contract address {contract_address} on chain {chain}")
        return None
    except Exception as e:
        logger.error(f"Error mapping contract address to CoinGecko coin_id: {e}")
        return None

# Function to fetch token market data from CoinGecko
def fetch_coingecko_data(coin_id):
    try:
        if not coin_id:
            return None
        response = requests.get(COINGECKO_COIN_DATA_URL.format(coin_id))
        if response.status_code != 200:
            logger.error(f"CoinGecko coin data API error: {response.status_code}")
            return None
        data = response.json()
        market_data = data.get('market_data', {})
        return {
            'market_cap': market_data.get('market_cap', {}).get('usd', 0),
            'price': market_data.get('current_price', {}).get('usd', 0),
            'volume': market_data.get('total_volume', {}).get('usd', 0)
        }
    except Exception as e:
        logger.error(f"Error fetching CoinGecko data: {e}")
        return None

# Function to fetch token data and identify top traders (synchronous)
def fetch_token_data_sync(contract_address, chain='eth'):
    try:
        # Check if data is cached
        token = TokenData.objects.filter(contract_address=contract_address, chain=chain).first()
        if token:
            logger.info(f"Using cached data for {contract_address} on chain {chain}")
            return token

        # Fetch market data from CoinGecko
        logger.info(f"Fetching CoinGecko data for {contract_address} on chain {chain}")
        coin_id = get_coingecko_coin_id(contract_address, chain)
        logger.info(f"CoinGecko coin_id: {coin_id}")
        coingecko_data = fetch_coingecko_data(coin_id) if coin_id else None
        if coingecko_data:
            market_cap = coingecko_data['market_cap']
            price = coingecko_data['price']
            volume = coingecko_data['volume']
            logger.info(f"CoinGecko data: market_cap={market_cap}, price={price}, volume={volume}")
        else:
            market_cap = 0
            price = 0
            volume = 0
            logger.info("No CoinGecko data found, using defaults: market_cap=0, price=0, volume=0")

        # Fetch from Bubblemaps API (map-data endpoint)
        params = {'token': contract_address, 'chain': chain}
        logger.info(f"Sending request to Bubblemaps API: {BUBBLEMAPS_API_URL} with params {params}")
        bubble_response = requests.get(BUBBLEMAPS_API_URL, params=params)
        logger.info(f"Bubblemaps API response status: {bubble_response.status_code}")
        logger.info(f"Bubblemaps API response content: {bubble_response.text}")
        if bubble_response.status_code != 200:
            logger.error(f"Bubblemaps API error: {bubble_response.status_code} - {bubble_response.text}")
            return None
        bubble_data = bubble_response.json()
        logger.info(f"Bubblemaps API data: {bubble_data}")

        # Fetch from Score API (map-metadata endpoint)
        score_params = {'chain': chain, 'token': contract_address}
        logger.info(f"Sending request to Score API: {SCORE_API_URL} with params {score_params}")
        score_response = requests.get(SCORE_API_URL, params=score_params)
        logger.info(f"Score API response status: {score_response.status_code}")
        logger.info(f"Score API response content: {score_response.text}")
        score_data = score_response.json()
        if score_data.get('status') != 'OK':
            logger.error(f"Score API error: {score_data.get('message', 'Unknown error')}")
            return None
        logger.info(f"Score API data: {score_data}")

        # Extract token data
        decentralization_score = score_data.get('decentralisation_score', 0)
        identified_supply = score_data.get('identified_supply', {})
        percent_in_cexs = identified_supply.get('percent_in_cexs', 0)
        percent_in_contracts = identified_supply.get('percent_in_contracts', 0)

        # Identify top traders from transfer data (links)
        links = bubble_data.get('links', [])
        trader_volume = defaultdict(float)
        connections = defaultdict(int)

        # Calculate trading volume per wallet based on links
        for link in links:
            source_idx = link.get('source')
            target_idx = link.get('target')
            forward = link.get('forward', 0)
            backward = link.get('backward', 0)

            # Map indices to wallet addresses
            nodes = bubble_data.get('nodes', [])
            source_address = nodes[source_idx]['address'] if source_idx < len(nodes) else None
            target_address = nodes[target_idx]['address'] if target_idx < len(nodes) else None

            if source_address and target_address:
                # Sum forward and backward transfers to get total trading volume for each wallet
                trader_volume[source_address] += forward + backward
                trader_volume[target_address] += forward + backward

                # Track connections (number of transfers between wallets)
                connection_key = tuple(sorted([source_address, target_address]))
                connections[connection_key] += 1

        # Get top 5 traders by volume
        top_traders = sorted(trader_volume.items(), key=lambda x: x[1], reverse=True)[:5]
        top_traders_dict = {trader: volume for trader, volume in top_traders}

        # Format connections for top traders
        trader_connections = {}
        top_trader_addresses = set(trader for trader, _ in top_traders)
        for (wallet1, wallet2), count in connections.items():
            if wallet1 in top_trader_addresses and wallet2 in top_trader_addresses:
                trader_connections[f"{wallet1}-{wallet2}"] = count

        # Cache the data
        token = TokenData.objects.create(
            contract_address=contract_address,
            chain=chain,
            market_cap=market_cap,
            price=price,
            volume=volume,
            decentralization_score=decentralization_score,
            percent_in_cexs=percent_in_cexs,
            percent_in_contracts=percent_in_contracts,
            top_traders=top_traders_dict,
            trader_connections=trader_connections
        )
        logger.info(f"Token data cached: {contract_address} on chain {chain}")
        return token
    except Exception as e:
        logger.error(f"Error fetching token data: {str(e)}")
        return None

# Async wrapper for fetch_token_data
async def fetch_token_data(contract_address, chain='eth'):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_token_data_sync, contract_address, chain)

# Function to take a screenshot of the bubble map (synchronous)
def take_bubble_map_screenshot_sync(contract_address):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')  # Required for some environments
        options.add_argument('--disable-dev-shm-usage')  # Prevent issues in Docker or limited environments
        options.add_argument('--disable-gpu')  # Disable GPU for headless mode
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # URL of the Django view rendering the bubble map
        url = f"http://127.0.0.1:8000/bubble_map/{contract_address}/"
        logger.info(f"Attempting to access URL: {url}")
        driver.get(url)
        driver.set_window_size(800, 600)
        # Wait for the chart to render (e.g., 5 seconds)
        import time
        time.sleep(5)
        screenshot_path = f"screenshot_{contract_address}.png"
        logger.info(f"Saving screenshot to: {screenshot_path}")
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return screenshot_path
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return None

# Async wrapper for take_bubble_map_screenshot
async def take_bubble_map_screenshot(contract_address):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, take_bubble_map_screenshot_sync, contract_address)

# Telegram bot handlers with retry logic
async def start(update: Update, context: ContextTypes):
    # Set up the menu button with retries
    bot = Bot(token=TELEGRAM_TOKEN)
    commands = [
        BotCommand("help", "Get help"),
        BotCommand("about", "About this bot"),
    ]
    for attempt in range(3):
        try:
            await bot.set_my_commands(commands)
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to set bot commands after multiple attempts.")
        return

    # Inline keyboard for start
    keyboard = [
        [InlineKeyboardButton("Analyze Token", callback_data="analyze_token")],
        [InlineKeyboardButton("Learn More", url="https://bubblemaps.io/")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send welcome message with retries
    for attempt in range(3):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Welcome to the Bubblemaps Bot! 💰📈\n"
                     "I can help you analyze top traders for any token. Send me a contract address to get started!\n"
                     "Please specify the chain (e.g., eth, bsc) if needed, default is eth.",
                reply_markup=reply_markup
            )
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to send welcome message after multiple attempts.")

async def button_callback(update: Update, context: ContextTypes):
    query = update.callback_query
    for attempt in range(3):
        try:
            await query.answer()
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to answer callback query after multiple attempts.")
        return

    if query.data == "analyze_token":
        for attempt in range(3):
            try:
                await query.message.reply_text("Please send me a token contract address to analyze.")
                break
            except TimedOut:
                logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                await asyncio.sleep(2)
        else:
            logger.error("Failed to send analyze token message after multiple attempts.")
    elif query.data == "view_visual":
        # Fetch the latest token data from context
        contract_address = context.user_data.get("last_contract_address")
        if not contract_address:
            for attempt in range(3):
                try:
                    await query.message.reply_text("Please analyze a token first by sending a contract address.")
                    break
                except TimedOut:
                    logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                    await asyncio.sleep(2)
            else:
                logger.error("Failed to send 'analyze token first' message after multiple attempts.")
            return

        token_data = await fetch_token_data(contract_address, chain=context.user_data.get("chain", "eth"))
        if not token_data:
            for attempt in range(3):
                try:
                    await query.message.reply_text("Sorry, I couldn't fetch data for that token.")
                    break
                except TimedOut:
                    logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                    await asyncio.sleep(2)
            else:
                logger.error("Failed to send 'couldn't fetch data' message after multiple attempts.")
            return

        # Take a screenshot of the bubble map with retries
        screenshot_path = None
        for attempt in range(3):
            try:
                screenshot_path = await take_bubble_map_screenshot(contract_address)
                break
            except TimedOut:
                logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                await asyncio.sleep(2)
        if not screenshot_path:
            for attempt in range(3):
                try:
                    await query.message.reply_text("Sorry, I couldn't generate the bubble map screenshot.")
                    break
                except TimedOut:
                    logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                    await asyncio.sleep(2)
            else:
                logger.error("Failed to send 'couldn't generate screenshot' message after multiple attempts.")
            return

        # Send the screenshot with retries
        for attempt in range(3):
            try:
                with open(screenshot_path, 'rb') as photo:
                    await query.message.reply_photo(photo=photo)
                break
            except TimedOut:
                logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                await asyncio.sleep(2)
        else:
            for attempt in range(3):
                try:
                    await query.message.reply_text("Failed to send the screenshot after multiple attempts.")
                    break
                except TimedOut:
                    logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                    await asyncio.sleep(2)
            else:
                logger.error("Failed to send 'failed to send screenshot' message after multiple attempts.")
            return

        # Clean up
        os.remove(screenshot_path)

async def handle_message(update: Update, context: ContextTypes):
    message_text = update.message.text.strip()
    # Check if the user specified a chain (e.g., "0x123... bsc")
    parts = message_text.split()
    contract_address = parts[0]
    chain = parts[1] if len(parts) > 1 else "eth"  # Default to eth if not specified

    context.user_data["last_contract_address"] = contract_address
    context.user_data["chain"] = chain
    for attempt in range(3):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Fetching data for contract address: {contract_address} on chain {chain}... 💰"
            )
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to send 'fetching data' message after multiple attempts.")
        return

    # Fetch token data
    token_data = await fetch_token_data(contract_address, chain=chain)
    if not token_data:
        for attempt in range(3):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sorry, I couldn't fetch data for that token. Please try another address."
                )
                break
            except TimedOut:
                logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
                await asyncio.sleep(2)
        else:
            logger.error("Failed to send 'couldn't fetch data' message after multiple attempts.")
        return

    # Prepare response with all required data
    response = (
        f"Token: {contract_address} (Chain: {chain})\n"
        f"Market Cap: ${token_data.market_cap:,.2f}\n"
        f"Price: ${token_data.price:,.4f}\n"
        f"Volume (24h): ${token_data.volume:,.2f}\n"
        f"Decentralization Score: {token_data.decentralization_score:.2f}%\n"
        f"Supply Distribution:\n"
        f"  - Percent in CEXs: {token_data.percent_in_cexs:.2f}%\n"
        f"  - Percent in Contracts: {token_data.percent_in_contracts:.2f}%\n"
    )

    # Inline keyboard for further actions
    keyboard = [
        [InlineKeyboardButton("View Trader Bubble Map", callback_data="view_visual")],
        [InlineKeyboardButton("Analyze Another Token", callback_data="analyze_token")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for attempt in range(3):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response,
                reply_markup=reply_markup
            )
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to send token data message after multiple attempts.")

async def help_command(update: Update, context: ContextTypes):
    for attempt in range(3):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💰 Bubblemaps Bot Help 📈\n"
                     "1. Send a token contract address to analyze top traders (e.g., '0x123...').\n"
                     "2. Optionally specify the chain (e.g., '0x123... bsc'). Default is eth.\n"
                     "3. Use the buttons to view the trader bubble map or analyze another token.\n"
                     "4. Use the menu for more options."
            )
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to send help message after multiple attempts.")

async def about_command(update: Update, context: ContextTypes):
    for attempt in range(3):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💰 Bubblemaps Bot 📈\n"
                     "I analyze the top traders of a token and show their connections, powered by Bubblemaps API.\n"
                     "Learn more at https://bubblemaps.io/"
            )
            break
        except TimedOut:
            logger.warning(f"Telegram API timed out on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to send about message after multiple attempts.")

# Main function to run the bot
def main():
    # Start the Telegram bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()

