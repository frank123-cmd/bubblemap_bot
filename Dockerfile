# Use a pre-built image with Chrome and ChromeDriver
FROM selenium/standalone-chrome:135.0

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN apt-get update && apt-get install -y python3 python3-pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Run Django migrations and collect static files
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Expose port 8000 for the Django server
EXPOSE 8000

# Command to run the Django server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
