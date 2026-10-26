import os
#import json
import pandas as pd
#import re

from uuid import uuid4
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

#from json_retrieval.retrieval_control import RetrievalController
from json_retrieval.prompts.prompts import SELECTION_PROMPT, SELECTION_SYSTEM_PROMPT


class Retriever():

    def __init__(self, vector_store_name = None, qdrant_url :str = None, vec_dim: int = 4096):

        if vector_store_name is None:
            vector_store_name = os.getenv("VECTOR_STORE_NAME")
        else:
            self.vector_store_name = vector_store_name
        #self.tracer = init_phoenix("json_retriever")
        #self.chunker = JSONChunker()
        
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("EMB_MODEL"),
            base_url=os.getenv("EMB_BASE_URL")
        )

        self.init_ollama()

        if qdrant_url is not None:
            self.qdr_client = QdrantClient(url = qdrant_url)
        else:
            self.qdr_client = QdrantClient(path=os.getenv("PROJECT_DIR")+"/json_retrieval/local_data/embeddings")
        self.create_collection(vector_store_name, vec_dim)

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
    """
    def retrieve_chunk(self, uuid):
        return self.chunker.return_chunk(uuid)
    """
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
            #collection = self.qdr_client.get_collection(name)
            self.qdr_client.create_payload_index(
                collection_name=name,
                field_name="metadata.id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    def set_vector_store(self,collection_name):
        self.vector_store = QdrantVectorStore(
            client=self.qdr_client,
            collection_name=collection_name,
            embedding=self.embeddings
        )
        return self.vector_store

    def retrieve_chunks(self, collection_name, query, source_ids:list[str], user_roles:list[str], limit:int = 20):
        
        if self.vector_store.collection_name != collection_name:
            self.set_vector_store(collection_name=collection_name)
        print(type(source_ids), source_ids)
        print(type(user_roles), user_roles)
        #filter = []
        filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.source_id",
                    match=models.MatchAny(any=source_ids),
                ),
                models.FieldCondition(
                    key="metadata.role_access",
                    match=models.MatchAny(any=user_roles),
                ),
            ]
        )
        """
        iterator = 0
        #for source in source_ids:
        filter.append(models.FieldCondition(
            key="metadata.source_id",
            match=models.MatchAny(
                any=source_ids
            ),
        ))
        #iterator +=1

        #for user_role in user_roles:
        filter.append(models.FieldCondition(
            key="metadata.role_access",
            match=models.MatchAny(
                any=user_roles
            ),
        ))
        #iterator +=1"""

        response =self.vector_store.similarity_search_with_score(
            #collection_name=collection_name,
            query=query,
            filter=filter,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            k=limit,
        )
        return response





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


   

    



    
    

