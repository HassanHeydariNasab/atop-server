import logging
import redis
from peewee import PostgresqlDatabase

db = PostgresqlDatabase(
    "atop",
    user="postgres",
    password="12345679",
    host="127.0.0.1",
    port=5432,
    autorollback=True,
)

logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

ranks = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
