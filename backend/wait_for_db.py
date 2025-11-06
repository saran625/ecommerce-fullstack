import time
import pymongo
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_mongodb():
    """Wait for MongoDB to be ready"""
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            client = pymongo.MongoClient(
                os.getenv('MONGO_URI', 'mongodb://mongodb:27017/'),
                serverSelectionTimeoutMS=5000
            )
            client.admin.command('ping')
            logger.info("✅ MongoDB is ready!")
            return True
        except Exception as e:
            attempt += 1
            logger.warning(f"⏳ Waiting for MongoDB... (attempt {attempt}/{max_attempts})")
            time.sleep(2)
    
    logger.error("❌ MongoDB failed to start within timeout")
    return False

if __name__ == "__main__":
    wait_for_mongodb()