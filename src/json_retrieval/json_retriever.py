import os
from dotenv import load_dotenv
import json
import pandas as pd
import re
import instructor

from opentelemetry.trace import StatusCode
from openai import OpenAI
from uuid import uuid4
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from process_mining_api.init_phoenix import init_phoenix
from process_mining_api.responsemodels.basic_response import BasicResponse
from json_retrieval.prompts.prompts import SELECTION_PROMPT, SELECTION_SYSTEM_PROMPT, TEST_PROMPT, TEST_SYSTEM_PROMPT, PERSONA_PROMPT, PERSONA_SYSTEM_PROMPT


class Retriever():

    def __init__(self, vector_store_name = None, qdrant_url :str = None, vec_dim: int = 4096):

        if vector_store_name is None:
            self.vector_store_name = os.getenv("VECTOR_STORE_NAME")
        else:
            self.vector_store_name = vector_store_name
        #self.tracer = init_phoenix("json_retriever")
        #self.chunker = JSONChunker()
        
        #self.embeddings = OpenAIEmbeddings(
        #    model=os.getenv("EMB_MODEL"),
        #    base_url=os.getenv("EMB_BASE_URL")
        #)

        self.init_ollama()

        if qdrant_url is not None:
            self.qdr_client = QdrantClient(url = qdrant_url)
        else:
            self.qdr_client = QdrantClient(path=os.getenv("PROJECT_DIR")+"/json_retrieval/local_data/embeddings")
        self.create_collection(self.vector_store_name, vec_dim)

        self.init_embeddings()
        

    def init_ollama(self):
        was_successfull = None
        try:
            self.embeddings = OpenAIEmbeddings(
                model=os.getenv("EMB_MODEL"),
                #validate_model_on_init=True,
                base_url=os.getenv("EMB_BASE_URL"),)
            was_successfull = True
        except Exception as e:
            print(e)
            was_successfull = False
        return was_successfull

    def init_embeddings(self):
        was_successfull = self.init_ollama()
        if was_successfull is not True:
            print("Embeddings not initialized. Cannot initialize vector store.")
        else:
            try:
                self.vector_store = QdrantVectorStore(
                    client=self.qdr_client,
                    collection_name=self.vector_store_name,
                    embedding=self.embeddings
                )
                self.embedder = Embedder(self.qdr_client,self.vector_store,self.embeddings)
            except Exception as e:
                print(e)
                print("Vector store not initialized. Cannot initialize vector store.")
                was_successfull = False

        return was_successfull           
    
    def retrieve(self, query, num_results=4):
        #query_emb = self.embedder.get_embedding(query,os.getenv("EMB_MODEL"))
        response = self.vector_store.similarity_search_with_score(query, k=num_results)
        return response
    
    def retrieve_chunk(self, uuid):
        return self.chunker.return_chunk(uuid)
    
    def embed_json(self,json_data):
        chunks = self.chunker.chunk_json(json_data)
        #self.create_collection(self.vector_store_name, vec_dim)
        embedding = self.embedder.create_json_embedding(chunks)

    def embed(self, collection_name:str, chunk_id: str, text: str, role_access: list[str], source_id: str = None):
        response = self.embedder.create_embedding(collection_name, chunk_id,text,role_access,source_id)

        return response

    def get_chunk_by_chunk_id(self,collection_name:str, chunk_id: str):
        chunk = self.qdr_client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.id",
                        match=models.MatchValue(value=chunk_id),
                    )
                ]
            ),
        )
        #print ("chunk:",chunk[0])
        if chunk[0] != []:
            return chunk[0][0]
        else:
            return None

    def delete_chunk(self,collection_name:str, chunk_id: str):
        chunk = self.get_chunk_by_chunk_id(collection_name=collection_name,chunk_id=chunk_id)
        if chunk is not None:
            self.qdr_client.delete(collection_name=collection_name, points_selector=[chunk.id])
            return True
        else:
            return False

    def create_collection(self, name:str, size: int = 4096):
        #Create new collection with the given name if it does not exist
        if not self.qdr_client.collection_exists(name):
            self.qdr_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
            collection = self.qdr_client.get_collection(name)
            self.qdr_client.create_payload_index(
                collection_name=collection.collection_name,
                field_name="metadata.id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )



class Embedder():
    
    def __init__(self,client,vector_store, embeddings):
        #super().__init__()
        #self.embeddings = embeddings
        self.client = client
        self.vector_store = vector_store
        self.embeddings = embeddings

    # TODO: Make this more flexible. Incorporate in Retreiver and let the vector_stroe be exchangeable 
    def create_embedding(self, collection_name, chunk_id: str, text: str, role_access: list[str], source_id: str = None):
        if self.vector_store.collection_name != collection_name:
            self.vector_store = QdrantVectorStore(self.client, collection_name, self.embeddings)
        response = self.vector_store.add_texts(texts= [text], metadatas=[{"id": chunk_id, "role_access": role_access, "source_id": source_id}],ids=[uuid4()])
        return response

    """
    def create_json_embedding(self,json_data):
        uuids = [str(uuid4()) for _ in range(len(json_data))]
        str_chunks = []
        #self.chunks = {}
        for i, chunk in enumerate(json_data):
            str_chunks.append(str(chunk))
            #self.chunks[uuids[i]] = chunk
        self.vector_store.add_texts(
            texts=str_chunks,
            ids=uuids)
    """
"""
class JSONChunker:
    
    def __init__(self):
        self.chunks = None

    def chunk_json(self, json):
        splitter = RecursiveJsonSplitter(max_chunk_size=300)
        self.chunks = splitter.split_json(json_data=json, convert_lists=True)  
        return self.chunks
    
    def return_chunk(self, uuid):
        return self.chunks[uuid]
"""


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

    def retrieve_chunks(self, query, search_criteria, documents):
        source_ids= search_criteria.source_ids
        user_roles= search_criteria.user_roles



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
    qdrant_url = "http://localhost:6333"
    retrieval_controller = RetrievalController("Default_collection",qdrant_url=qdrant_url)
    """
    retrieval_controller.update_chunk(
        chunk_id= "Test_id1",
        text= text,
        role_access=["admin","user", "user2"],
        source_id="Datensystem_1")"""
    retrieval_controller.update_chunk(
            collection_name= "Default_collection",
            chunk_id= "Test_id2",
            text= text,
            role_access=["admin","user", "user2"],
            source_id="Datensystem_1")
    resp= retrieval_controller.get_chunk_by_chunk_id("Default_collection","Test_id2")
    print(resp)
    #resp_1= retrieval_controller.retriever.delete_chunk("Default_collection","Test_id2")
    #print(resp_1)
    #embedding_creation(vec_dim=2560)
    #json_embedder = JSONEmbedder()

    

    #json_data = controller.load_data("Datenmodell-2026-06-10_18-13-17-Entwicklung.json")
    
    #controller.re_chunk_json(json_data)

    #controller.json_retriever.embed_json(json_data)

    #query = "Wie funktioniert ein Dateiupload?"
    #query = "Wei kann ich ein Objekt erstellen?"
    #response = controller.simple_query(query)
    #print("Response: ", response)
    

    """
    df_chunks = pd.DataFrame(response,columns=["output","value"])
    print(df_chunks)
    df_chunks.loc[0]["output"]
    id = response[0][0]
    print(id)
    label, id = controller.get_id_label(
        df_chunks.loc[0]["output"].page_content,
        df_chunks.loc[0]["output"].metadata)
    print(label, id)
    print(controller.get_labels(response))
    print(df_chunks.loc[5]["output"])
    #json_retriever.retrieve_chunk(id)"""

    



    
    

