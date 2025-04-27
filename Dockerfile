# Use a pre-built image with Chrome and ChromeDriver
FROM selenium/standalone-chrome:135.0

# Set working directory
WORKDIR /app

# Fix apt-get issues and install Python dependencies
USER root
RUN mkdir -p /var/lib/apt/lists/partial && \
    chmod -R 755 /var/lib/apt/lists && \
    rm -f /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Run Django migrations and collect static files
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Expose port 8000 for the Django server
EXPOSE 8000

# Command to run the Django server
CMD ["gunicorn", "bubblemaps_bot.wsgi:application", "--bind", "0.0.0.0:8000"]
