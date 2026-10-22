from json_retrieval.json_retriever import Retriever
from json_retrieval.prompts.prompts import PERSONA_PROMPT, PERSONA_SYSTEM_PROMPT, TEST_PROMPT, TEST_SYSTEM_PROMPT
from process_mining_api.init_phoenix import init_phoenix
from process_mining_api.responsemodels.basic_response import BasicResponse


import instructor
from dotenv import load_dotenv
from openai import OpenAI
from opentelemetry.trace import StatusCode


import os


class RetrievalController:

    def __init__(self, vector_store_name, qdrant_url:str = None, vec_dim :int = 4096):
        load_dotenv()
        self.retriever = Retriever(vector_store_name, qdrant_url, vec_dim)
        self.tracer = init_phoenix("json_doc-retrieval")
        self.client = self.init_client()

    def init_client(self):
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL"))
        client = instructor.from_openai(client, mode=instructor.Mode.JSON, )
        return client

    def test_query(self, query: str, model: str, persona: str = None):
        if persona is None:
            prompt = TEST_PROMPT.format(user_query=query)
            system_prompt = TEST_SYSTEM_PROMPT
        else:
            prompt = PERSONA_PROMPT.format(user_query=query)
            system_prompt = PERSONA_SYSTEM_PROMPT.format(persona=persona)

        with self.tracer.start_as_current_span("Test_Response", openinference_span_kind="agent") as span:
            span.set_input(prompt)

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_model=BasicResponse
            )
            span.set_output(response.model_dump())
            span.set_status(StatusCode.OK)
        return response

    def retrieve_chunks(self, collection_name, query, search_criteria, documents=None):
        source_ids= search_criteria.source_ids
        user_roles= search_criteria.user_roles
        #TODO Add documents to retrieval?
        return self.retriever.retrieve_chunks(
            collection_name=collection_name,
            query = query,
            source_ids= source_ids,
            user_roles= user_roles)


    def user_query(
            self,
            query: str,
            model: str,
            persona: str,
            retrieved_chunks: str = None):
        pass

    def init_embeddings(self):
        self.retriever.init_ollama()
        self.retriever.init_embeddings()

    def get_models(self):
        models = self.client.models.list()
        return models

    def update_chunk(self, collection_name: str, chunk_id: str, text: str, role_access: list[str], source_id: str = None):
        self.retriever.create_collection(collection_name)
        if self.get_chunk_by_chunk_id(collection_name, chunk_id) is not None:
            self.delete_chunk(collection_name, chunk_id)
            was_updated = True
        else:
            was_updated = False
        self.retriever.embed(collection_name, chunk_id,text,role_access,source_id)
        return was_updated


    def get_chunk_by_chunk_id(self, collection_name: str, chunk_id: str):
        return self.retriever.get_chunk_by_chunk_id(collection_name,chunk_id)

    def delete_chunk(self, collection_name: str, chunk_id: str):
        return self.retriever.delete_chunk(collection_name=collection_name,chunk_id=chunk_id)



def embedding_creation(vec_dim: int):
    vector_store_name = os.getenv("VECTOR_STORE_NAME")

    qdrant_url = "http://localhost:6333/"
    
    controller = RetrievalController(vector_store_name, qdrant_url, vec_dim)

    json_data = controller.load_data("Datenmodell-2026-06-10_18-13-17-Entwicklung.json")
        
    controller.re_chunk_json(json_data)
    
    controller.retriever.embed_json(json_data)

    query = "Wie kann ich ein Objekt erstellen?"

    json_response = controller.simple_query_json(query)
    print(json_response)

    query_response = controller.simple_llm_response(query)
    print(query_response)
    controller.retriever.qdr_client.close()



if __name__ == "__main__":

    text = """
    1. Der letzte Regenschirm

    Jeden Morgen stellte Daniel einen Regenschirm vor seine Wohnungstür.

    Er brauchte ihn nicht. Es war immer sonnig.

    Eines Tages klopfte ein kleines Mädchen an seine Tür.

    „Gehört der dir?“, fragte sie und hielt den Regenschirm hoch.

    „Nein“, sagte Daniel. „Er gehört demjenigen, der ihn braucht.“

    Das Mädchen lächelte und nahm ihn.

    Am Nachmittag begann es zum ersten Mal seit Jahren zu regnen.

    Daniel stand draußen und wurde völlig nass.

    Plötzlich hielt jemand einen Regenschirm über seinen Kopf.

    Es war das kleine Mädchen.

    „Sieht so aus, als würdest du ihn heute brauchen“, sagte sie.
    """
    persona = "Du bist ein entspannter Kollege."

    qdrant_url = "http://localhost:6333"
    retrieval_controller = RetrievalController("Default_collection",qdrant_url=qdrant_url)
    """
    retrieval_controller.update_chunk(
        chunk_id= "Test_id1",
        text= text,
        role_access=["admin","user", "user2"],
        source_id="Datensystem_1")
    retrieval_controller.update_chunk(
            collection_name= "Default_collection",
            chunk_id= "Test_id2",
            text= text,
            role_access=["admin","user", "user2"],
            source_id="Datensystem_1")
    resp= retrieval_controller.get_chunk_by_chunk_id("Default_collection","Test_id2")
    print(resp)"""
    #from pydantic import BaseModel
    #class SearchCriteria(BaseModel):
    #    source_ids: list[str] = []
    #    user_roles: list[str] = []

    #search_criteria=SearchCriteria(source_ids=[],user_roles=[])

    #chunks =retrieval_controller.retrieve_chunks("Default_collection",text,search_criteria=search_criteria)
    #print(chunks)

    answer=retrieval_controller.get_chunk_by_chunk_id("Default_collection",chunk_id="Test_id2")
    print(answer.payload["page_content"], answer.payload["metadata"]["source_id"],answer.payload["metadata"]["role_access"])
