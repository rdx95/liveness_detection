from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class MongoDBClient:
    def __init__(self, connection_string:str, db_name:str):
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
        except ConnectionFailure as e:
            raise Exception(f"Failed to connect to MongoDB: {e}")

    def check_connection(self):
        try:
            self.client.admin.command('ismaster')
            return True
        except ConnectionFailure:
            return False

    def create_document(self, collection_name, data):
        try:
            collection = self.db[collection_name]
            result = collection.insert_one(data)
            return result.inserted_id
        except Exception as e:
            raise Exception(f"Failed to create document: {e}")

    def read_documents(self, collection_name, query=None):
        try:
            collection = self.db[collection_name]
            if query is None:
                return list(collection.find())
            else:
                return list(collection.find(query))
        except Exception as e:
            raise Exception(f"Failed to read documents: {e}")

    def update_document(self, collection_name, query, data):
        try:
            collection = self.db[collection_name]
            result = collection.update_one(query, {'$set': data})
            return result.modified_count
        except Exception as e:
            raise Exception(f"Failed to update document: {e}")

    def delete_document(self, collection_name, query):
        try:
            collection = self.db[collection_name]
            result = collection.delete_one(query)
            return result.deleted_count
        except Exception as e:
            raise Exception(f"Failed to delete document: {e}")