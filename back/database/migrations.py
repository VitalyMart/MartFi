from .database import engine, Base
from .models import User, Stock
import logging

logger = logging.getLogger(__name__)

def create_all_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully")

if __name__ == "__main__":
    create_all_tables()