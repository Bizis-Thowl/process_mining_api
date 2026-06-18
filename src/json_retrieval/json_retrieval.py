import os
from dotenv import load_dotenv
#import instructor
import json
import pandas as pd
import re

from uuid import uuid4
#from retriever import doc_retriever, doc_chunker, doc_embedder
#from retriever.init_phoenix import init_phoenix
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_ollama import OllamaEmbeddings

class JSONRetriever():
    """
    Future work will happen in process_mining_api!
    """
    def __init__(self, collection_name ="json_embedding"):
        
        self.collection_name = collection_name
        #self.tracer = init_phoenix("json_retriever")
        self.chunker = JSONChunker()
        
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMB_MODEL"),
            validate_model_on_init=True,
            base_url=os.getenv("EMB_BASE_URL"))
        
        self.client = QdrantClient(path=os.getenv("PROJECT_DIR")+"/json_retrieval/local_data/embeddings")
        self.create_collection(self.collection_name)
        
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings
        )
        
        self.embedder = JSONEmbedder(self.embeddings,self.client,self.vector_store)
    
    def retrieve(self, query, num_results=4):
        #query_emb = self.embedder.get_embedding(query,os.getenv("EMB_MODEL"))
        response = self.vector_store.similarity_search_with_score(query, k=num_results)
        return response
    
    def retrieve_chunk(self, uuid):
        return self.chunker.return_chunk(uuid)
    
    def embed_json(self,json_data):
        chunks = self.chunker.chunk_json(json_data)
        self.create_collection(self.collection_name)
        embedding = self.embedder.create_json_embedding(chunks)

    def create_collection(self, name:str):
        #Create new collection with the given name if it does not exist
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=4096, distance=Distance.COSINE),
            )



class JSONEmbedder():
    
    def __init__(self,embeddings,client,vector_store):
        super().__init__()
        self.embeddings = embeddings
        self.client = client
        self.vector_store = vector_store

    def create_json_embedding(self,json_data):
        uuids = [str(uuid4()) for _ in range(len(json_data))]
        str_chunks = {}
        self.chunks = {}
        for i, chunk in enumerate(json_data):
            str_chunks[uuids[i]]= str(chunk)
            self.chunks[uuids[i]] = chunk
        self.vector_store.add_texts(
            texts=str_chunks,
            ids=uuids)


class JSONChunker:
    
    def __init__(self):
        self.chunks = None

    def chunk_json(self, json):
        splitter = RecursiveJsonSplitter(max_chunk_size=300)
        self.chunks = splitter.split_json(json_data=json, convert_lists=True)  
        return self.chunks
    
    def return_chunk(self, uuid):
        return self.chunks[uuid]



class RetrievalController:

    def __init__(self, collection_name):
        load_dotenv()
        self.json_retriever = JSONRetriever(collection_name)
        

    def load_data(self, filename):
        with open(f"src\json_retriever\local_data\{filename}", "r", encoding="utf-8") as f:
            json_data = json.load(f)
        return json_data

    def re_chunk_json(self, json_data):
        self.json_retriever.chunker.chunk_json(json_data)
    
    def get_id_label(self, chunk, metadata):
        # Recieves a String of a chunk and its metadata and returns the a label and id
        label_pattern = re.compile(r"'label': \{'de':\s*'(.*?)'",  flags=re.MULTILINE) #TODO: add {'tooltiplabelid': ??
        id_pattern = re.compile(r"'_id': '(.*?)'")
        label = re.findall(label_pattern,chunk)[0]
        id = metadata["_id"]
        return label, id
    
    def get_labels(self, chunks):
        df_chunks = pd.DataFrame(chunks,columns=["output","value"])
        label_pattern = re.compile(r"'label': \{'de':\s*'(.*?)'",  flags=re.MULTILINE)
        df_labels = pd.DataFrame(columns=["id","label"])
        for i, row in df_chunks.iterrows():
            doc= row["output"]
            label = re.findall(label_pattern,doc.page_content)
            id = doc.metadata["_id"]
            df_labels.loc[i]=[id,label]
        return df_labels

    def simple_query(self, query):
        return self.json_retriever.retrieve(query,25)


if __name__ == "__main__":
   
    
    #json_embedder = JSONEmbedder()

    collection_name = "json_collection_2"

    controller = RetrievalController(collection_name)

    json_data = controller.load_data("Datenmodell-2026-06-10_18-13-17-Entwicklung.json")
    
    controller.re_chunk_json(json_data)

    #json_retriever.embed_json(json_data)

    
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
    #json_retriever.retrieve_chunk(id)
    controller.json_retriever.client.close()



    
    

