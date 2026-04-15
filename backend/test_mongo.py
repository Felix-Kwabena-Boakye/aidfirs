import os
from dotenv import load_dotenv
load_dotenv()
print('Testing MongoDB connection...')
print('URI: ', repr(os.getenv('MONGO_URI'))[:60] + '...')
from mongo_connection import health_check, get_users_collection
print(health_check())
collection = get_users_collection()
print('Collection OK. Indexes:', len(list(collection.list_indexes())))
print('SUCCESS! Ready for Django.')

