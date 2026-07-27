import datetime
import os

from json_retrieval.json_retriever import RetrievalController


class QueryHandler():
    def __init__(self, vector_store_name = None, qdrant_url ="http://localhost:6333/"):
        if vector_store_name is None:
            vector_store_name = os.getenv("VECTOR_STORE_NAME")
        self.__retriever_controller = RetrievalController(vector_store_name,qdrant_url)
        #except Exception as e:
        #print(e)

    def simple_query(self, query: str):
        response = self.__retriever_controller.simple_query_json(query)
        #df_labels = self.__retriever_controller.get_labels(response)
        return response
    
    def simple_question(self, query: str):
        response = self.__retriever_controller.simple_llm_response(query)
        return response

    def set_tracing_id(self, tracing_id: str):
        self.__retriever_controller.set_tracing_id(tracing_id)