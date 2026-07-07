import datetime
import os

from json_retrieval.json_retriever import RetrievalController


class QueryHandler():
    def __init__(self, collection_name = None, qdrant_url ="http://localhost:6333/"):
        if collection_name is None:
            collection_name = os.getenv("COLLECTION_NAME")
        try:
            self.__retriever_controller = RetrievalController(collection_name,qdrant_url)
        except Exception as e:
            print(e)

    def simple_query(self, query: str, ):
        response = self.__retriever_controller.simple_query_json(query)
        #df_labels = self.__retriever_controller.get_labels(response)
        return response
    
    def simple_question(self, query: str):
        response = self.__retriever_controller.simple_llm_response(query)
        return response