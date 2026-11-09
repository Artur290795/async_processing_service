import os

# Settings are constructed while importing the application modules.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
