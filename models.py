# models.py

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the database engine
engine = create_engine('sqlite:////tmp/orders.db', echo=True)  # Save the database in the writable /tmp directory  # This will create a SQLite database file called 'orders.db'

# Create a base class for the models
Base = declarative_base()

# Define an Order model (example table)
class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    customer_name = Column(String)
    email = Column(String)
    phone = Column(String)
    total_amount = Column(Integer)
    status = Column(String)  # e.g., "Paid"


# Tracks which Chip In purchases we have already turned into Shopify orders,
# so retried/duplicate webhook deliveries never create a second order.
# chip_in_id is the primary key -> a UNIQUE constraint for free (atomic claim).
class ProcessedPurchase(Base):
    __tablename__ = 'processed_purchases'

    chip_in_id = Column(String, primary_key=True)
    shopify_order_id = Column(String)
    status = Column(String)  # "processing" | "done"

# Create the table
Base.metadata.create_all(engine)

# Set up the session
Session = sessionmaker(bind=engine)
session = Session()