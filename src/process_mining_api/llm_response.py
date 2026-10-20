import datetime
import os

from json_retrieval.json_retriever import RetrievalController
from json_retrieval.local_data.model_information import INFORMATION


class QueryHandler():
    def __init__(self, vector_store_name = None, qdrant_url ="http://localhost:6333/"):
        if vector_store_name is None:
            vector_store_name = os.getenv("VECTOR_STORE_NAME")
        self.__retriever_controller = RetrievalController(vector_store_name,qdrant_url)
        #self.model_handler = ModelHandler(self.__retriever_controller)
        #except Exception as e:
        #print(e)
    """
    def simple_query(self, query: str):
        response = self.__retriever_controller.simple_query_json(query)
        #df_labels = self.__retriever_controller.get_labels(response)
        return response
    
    def simple_question(self, query: str):
        response = self.__retriever_controller.simple_llm_response(query)
        return response

    def set_tracing_id(self, tracing_id: str):
        self.__retriever_controller.set_tracing_id(tracing_id)

    def test_model(self, query: str, model: str):
        response = self.__retriever_controller.test_query(query, model)
        return response
    """
    def test_persona(self, query: str, model: str, persona: str):
        response = self.__retriever_controller.test_query(query, model, persona)
        return response

    def update_chunk(self, chunk):
        response = self.__retriever_controller.update_chunk(
            collection_name = chunk.collection_name,
            chunk_id = chunk.chunk_id,
            text= chunk.text,
            role_access = chunk.role_access,
            source_id = chunk.source_id)
        return response

    def delete_chunk(self, chunk_id):
        response = self.__retriever_controller.delete_chunk(
            collection_name="Default_collection",
            chunk_id=chunk_id)
        return response

    def get_models(self):
        models = self.__retriever_controller.get_models()
        response = []
        for m in INFORMATION["list"]:
            for model in models:
                if m["id"] == model.id:
                    if hasattr(model, "max_input_tokens"):
                         response.append({
                            "name":m["id"],
                            "description":m["description"],
                            "max_input_tokens": model.max_input_tokens,
                            "max_output_tokens": model.max_output_tokens,
                            "multimodal": m["multimodal"],
                            "additional_info": m["additional_info"]})
        return response

    def user_query(self, user_query):
        retrieved_chunks = None
        if user_query.with_doc_search:
            retrieved_chunks = self.__retriever_controller.retrieve_chunks(
                query = user_query.query,
                search_criteria= user_query.search_criteria,
                documents = user_query.documents
            )
        response = self.__retriever_controller.user_query(
            query = user_query.query,
            model = user_query.model,
            persona = user_query.persona,
            retrieved_chunks= retrieved_chunks
        )
        return response

if __name__ == "__main__":
    query_handler = QueryHandler()
    query_handler.get_models()