# bot/views.py
from django.shortcuts import render
from bot.bot import fetch_token_data_sync  # Import the synchronous version directly

def bubble_map(request, contract_address):
    # Fetch the token data using the synchronous fetch_token_data
    token_data = fetch_token_data_sync(contract_address)

    if not token_data:
        return render(request, 'bubblemaps.html', {'error': 'Token data not found'})

    # Prepare data for the template
    context = {
        'contract_address': contract_address,
        'top_traders': token_data.top_traders,  # Access from token_data
        'trader_connections': token_data.trader_connections,  # Access from token_data
    }

    return render(request, 'bubblemaps.html', context)