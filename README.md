# Bubblemaps Bot

The Bubblemaps Bot is a Telegram bot that analyzes top traders for any token using data from the Bubblemaps API, Score API, and CoinGecko API. It provides insights into token market data, decentralization metrics, and visualizes trader relationships through an interactive bubble map. The bot is built with Python, Django, and Chart.js, and uses Selenium for screenshot generation.

---

## Features

* **Token Analysis**: Fetches and caches token data, including market cap, price, volume, decentralization score, and supply distribution.
* **Top Traders Visualization**: Identifies the top 5 traders by volume and visualizes their connections in a bubble map.
* **Bubble Map Improvements**:
    * Bubbles scale by trading volume for clear visual differentiation.
    * Static labels display trader addresses and volumes.
    * Connection lines between traders show the number of transfers with labels.
    * A force simulation positions bubbles to reflect relationships (connected traders are closer together).
* **Robust Telegram Integration**: Includes retry logic to handle temporary Telegram API timeouts.
* **Screenshot Generation**: Uses Selenium to capture the bubble map and send it to Telegram users.

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

* Python 3.13
* Django 4.2
* Google Chrome (for Selenium screenshot generation)
* Git
* A Telegram account and bot token (create a bot via BotFather)
* API keys for:
    * Bubblemaps API (for trader data)
    * Score API (for decentralization metrics)
* (Optional) CoinGecko API (for market data; public API used by default)

---

## Setup Instructions

1.  **Clone the Repository**
    Clone the project repository from GitHub:
    ```bash
    git clone [https://github.com/your-username/bubblemaps-bot.git](https://github.com/your-username/bubblemaps-bot.git)
    cd bubblemaps-bot
    ```

2.  **Set Up a Virtual Environment**
    Create and activate a virtual environment to manage dependencies:
    ```bash
    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install Dependencies**
    Install the required Python packages using `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    *Sample `requirements.txt`:*
    ```ini
    django==4.2
    python-telegram-bot[ext]==22.0
    requests==2.31.0
    selenium==4.16.0
    webdriver-manager==4.0.1
    python-dotenv==1.0.0
    asgiref==3.7.2
    httpx==0.27.0
    # Add other dependencies like Chart.js if managed via pip, otherwise note manual inclusion
    ```
    *(Note: Updated `python-telegram-bot` install command to include `[ext]` which is often needed)*

4.  **Configure Environment Variables**
    Create a `.env` file in the project root directory and add the following environment variables:
    ```env
    TELEGRAM_TOKEN=your-telegram-bot-token
    BUBBLEMAPS_API_URL=[https://api-legacy.bubblemaps.io/map-data](https://api-legacy.bubblemaps.io/map-data) # Corrected URL based on previous info
    BUBBLEMAPS_API_KEY=your-bubblemaps-api-key
    SCORE_API_URL=[https://api-legacy.bubblemaps.io/map-metadata](https://api-legacy.bubblemaps.io/map-metadata) # Corrected URL based on previous info
    SCORE_API_KEY=your-score-api-key

    # Optional: Add Django Secret Key and Database details if needed
    DJANGO_SECRET_KEY=your-django-secret-key
    DB_NAME=bubblemaps_db
    DB_USER=root
    DB_PASSWORD=your_db_password
    DB_HOST=localhost
    DB_PORT=3306
    DEBUG=True
    ```
    Replace the placeholder values with your actual API keys, bot token, and database credentials. *(Note: Corrected API URLs based on previous Gist info)*

5.  **Set Up Django**
    Initialize the Django database and apply migrations:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

6.  **Test the Setup**
    Run the Django development server to ensure everything is set up correctly:
    ```bash
    python manage.py runserver
    ```
    Visit `http://127.0.0.1:8000/bubble_map/0x1f9840a85d5af5bf1d1762f925bdaddc4201f984/` (or another relevant contract address) in your browser to test the bubble map view directly.

---

## Usage

1.  **Run the Bot**
    Start the Django server (if not already running) and the bot in separate terminals:

    *Terminal 1 (Django Server):*
    ```bash
    python manage.py runserver
    ```

    *Terminal 2 (Bot):*
    ```bash
    python -m bot.bot
    ```

2.  **Interact with the Bot on Telegram**
    * Start a chat with your bot on Telegram.
    * Use the `/start` command to initialize the bot.
    * Send a token contract address, optionally followed by the chain identifier (default is `eth`). Example: `0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 eth`
    * The bot will fetch and display token data, including market cap, price, volume, and decentralization metrics.
    * Click the "View Trader Bubble Map" button to receive a screenshot of the visualization.
    * Use `/help` for usage instructions or `/about` for more information about the bot.

**Example Interaction:**

> **You:** `0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 eth`
>
> **Bot Response:**
> ```
> Token: 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 (Chain: eth)
> Market Cap: $1,234,567.89
> Price: $5.6789
> Volume (24h): $123,456.78
> Decentralization Score: 75.50%
> Supply Distribution:
>  - Percent in CEXs: 20.00%
>  - Percent in Contracts: 15.00%
> ```
> *(Button: View Trader Bubble Map)*

---

## Project Structure

```
bubblemaps-bot/
├── bot/
│   ├── migrations/      # Database migration files
│   ├── templates/       # HTML Templates
│   │   └── bubblemaps.html
│   ├── __init__.py
│   ├── admin.py         # Django admin configurations (optional)
│   ├── apps.py          # Django app configuration
│   ├── bot.py           # Main bot logic
│   ├── models.py        # Django model(s)
│   ├── settings.py      # Django project settings (likely referenced by manage.py/env vars)
│   ├── urls.py          # Django URL routing for the bot app
│   ├── views.py         # Django view(s)
│   └── tests.py         # Unit/integration tests (optional)
├── manage.py            # Django management script
├── .env                 # Environment variables (should be in .gitignore)
├── .gitignore           # Specifies intentionally untracked files
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

---

## Key Components

* **`bot/bot.py`**: Handles Telegram bot interactions (commands, messages, callbacks). Fetches data from Bubblemaps, Score, and CoinGecko APIs. Caches data using the Django ORM (`bot/models.py`). Takes screenshots using Selenium. Implements retry logic for Telegram API calls.
* **`bot/views.py`**: Defines the `bubble_map` Django view. Retrieves cached token data (top traders, connections) and passes it to the HTML template (`bubblemaps.html`).
* **`bot/templates/bubblemaps.html`**: Uses Chart.js (likely included via CDN or static files) to render the interactive bubble map based on data passed from the view. Implements features like bubble scaling, labels, connection lines, force simulation, and signals rendering completion for screenshotting.
* **`bot/models.py`**: Defines the `TokenData` Django model used for caching API responses in the database.

---

## Deployment to GitHub

1.  **Initialize Git** (if not already done):
    ```bash
    git init
    ```

2.  **Create a `.gitignore` File**:
    Ensure sensitive and unnecessary files/directories are ignored. Example:
    ```gitignore
    # Virtual Environment
    .venv/
    venv/
    env/

    # Environment variables
    .env*

    # Python cache
    *.pyc
    __pycache__/

    # Django DB file (if using SQLite locally for testing)
    *.sqlite3
    db.sqlite3

    # Screenshot files
    screenshot_*.png

    # IDE / OS specific
    .idea/
    .vscode/
    *.DS_Store
    ```

3.  **Commit the Code**:
    ```bash
    git add .
    git commit -m "Initial commit of Bubblemaps Bot"
    ```

4.  **Create a GitHub Repository**:
    Go to GitHub and create a new repository (e.g., `bubblemaps-bot`).

5.  **Push to GitHub**:
    ```bash
    git remote add origin [https://github.com/your-username/bubblemaps-bot.git](https://github.com/your-username/bubblemaps-bot.git)
    git branch -M main
    git push -u origin main
    ```
    *(Replace `your-username` and repository name)*

---

## Contributing

Contributions are welcome! To contribute:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature`).
3.  Make your changes and commit them (`git commit -m "Add your feature"`).
4.  Push to your fork (`git push origin feature/your-feature`).
5.  Open a pull request on the original repository's `main` branch.

Please ensure your code follows PEP 8 style guidelines and includes appropriate tests where applicable.

---

## Troubleshooting

* **Blank Bubble Map Screenshot**:
    * Ensure the Django server is running (`python manage.py runserver`).
    * Check the browser console in the Selenium-controlled browser for JavaScript errors (run Selenium in non-headless mode temporarily for debugging).
    * Verify that the JavaScript logic correctly signals completion (e.g., updates the `renderComplete` element) and that Selenium is waiting for it appropriately.
* **Telegram API Timeouts**:
    * The bot includes basic retry logic. If timeouts persist, consider increasing the `read_timeout` and `write_timeout` values when building the `Application` in `bot.py`:
        ```python
        application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(20).write_timeout(20).build()
        ```
* **Selenium Connection Refused/Errors**:
    * Ensure the Django server is running and accessible at `http://127.0.0.1:8000/`.
    * Verify `webdriver-manager` has downloaded the correct ChromeDriver version compatible with your installed Google Chrome. Check firewall settings if necessary.
* **API Errors (401, 400, etc.)**:
    * Double-check your API keys and URLs in the `.env` file. Ensure they are correct and haven't expired.
    * Verify the contract address and chain ID sent to the bot are valid.
    * Check the specific API documentation for rate limits or potential issues.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details. (You would need to create a `LICENSE` file containing the MIT License text).

---

## Acknowledgments

* **Bubblemaps**: For providing the core trader data and decentralization metrics via their APIs.
* **CoinGecko**: For providing token market data.
* **Chart.js**: For the powerful JavaScript charting library used for visualization.
* **python-telegram-bot**: For the excellent library simplifying Telegram Bot API interactions.
* **Django**: For the web framework facilitating data caching and rendering the map view.
* **Selenium & WebDriver Manager**: For browser automation and screenshot generation.
```