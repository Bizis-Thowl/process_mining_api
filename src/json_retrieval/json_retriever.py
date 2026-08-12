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
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from process_mining_api.init_phoenix import init_phoenix
from process_mining_api.responsemodels.basic_response import BasicResponse
from json_retrieval.prompts.prompts import SELECTION_PROMPT, SELECTION_SYSTEM_PROMPT, TEST_PROMPT, TEST_SYSTEM_PROMPT, PERSONA_PROMPT, PERSONA_SYSTEM_PROMPT


class JSONRetriever():
    """
    Future work will happen in process_mining_api!
    """
    def __init__(self, vector_store_name ="json_embedding", qdrant_url :str = None, vec_dim: int = 4096):
        
        self.vector_store_name = vector_store_name
        #self.tracer = init_phoenix("json_retriever")
        self.chunker = JSONChunker()
        
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
            self.embeddings = OllamaEmbeddings(
                model=os.getenv("EMB_MODEL"),
                validate_model_on_init=True,
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
                self.embedder = JSONEmbedder(self.qdr_client,self.vector_store)
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

    def create_collection(self, name:str, size: int = 4096):
        #Create new collection with the given name if it does not exist
        if not self.qdr_client.collection_exists(name):
            self.qdr_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )



class JSONEmbedder():
    
    def __init__(self,client,vector_store):
        super().__init__()
        #self.embeddings = embeddings
        self.client = client
        self.vector_store = vector_store

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

    def __init__(self, vector_store_name, qdrant_url:str = None, vec_dim :int = 4096):
        load_dotenv()
        self.json_retriever = JSONRetriever(vector_store_name, qdrant_url, vec_dim)
        self.tracer = init_phoenix("json_doc-retrieval")
        self.client = self.init_client()

    def init_client(self):
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL"))
        client = instructor.from_openai(client, mode=instructor.Mode.JSON, )
        return client

    def set_tracing_id(self, tracing_id: str):
        self.tracer = init_phoenix(tracing_id)
        

    def load_data(self, filename):
        with open( f"src/json_retrieval/local_data/{filename}", "r", encoding="utf-8") as f:
            json_data = json.load(f)
        return json_data

    def re_chunk_json(self, json_data):
        self.json_retriever.chunker.chunk_json(json_data)
    
    def get_id_label(self, chunk, metadata):
        # Recieves a String of a chunk and its metadata and returns the a label and id
        label_pattern = re.compile(r"'label': \{'de':\s*'(.*?)'",  flags=re.MULTILINE) #TODO: add {'tooltiplabelid': ??
        #id_pattern = re.compile(r"'_id': '(.*?)'")
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
    
    def simple_query_json(self, query: str)-> dict: 
        response_list = self.simple_query(query)
        json_list = []
        for i, doc in enumerate(response_list):
            content = doc[0].page_content.replace("\'","\"")
            json_list.append({"page_content": content, "metadata": doc[0].metadata})
        #raw_str = raw_str.replace("\'","\"")
        #json_obj = json.loads(raw_str)
        return json_list
    

    def create_prompt(self, search_result: str, query_str: str):
        prompt = SELECTION_PROMPT.format(json_response=search_result, user_query=query_str)    
        return prompt
    
    def simple_llm_response(self, query :str, response_model = BasicResponse):
        MODEL = os.getenv("MODEL")
        json_response = self.simple_query_json(query)
        print(json_response)
        prompt = self.create_prompt(json_response, query)
        with self.tracer.start_as_current_span("LLM_Response", openinference_span_kind="agent") as span:
            span.set_input(prompt)
            
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SELECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_model=response_model
            )
            span.set_output(response.model_dump())
            span.set_status(StatusCode.OK)
        return response

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

    def init_embeddings(self):
        self.json_retriever.init_ollama()
        self.json_retriever.init_embeddings()
    
        
def embedding_creation(vec_dim: int):
    vector_store_name = os.getenv("VECTOR_STORE_NAME")

    qdrant_url = "http://localhost:6333/"
    
    controller = RetrievalController(vector_store_name, qdrant_url, vec_dim)

    json_data = controller.load_data("Datenmodell-2026-06-10_18-13-17-Entwicklung.json")
        
    controller.re_chunk_json(json_data)
    
    controller.json_retriever.embed_json(json_data)

    query = "Wie kann ich ein Objekt erstellen?"

    json_response = controller.simple_query_json(query)
    print(json_response)

    query_response = controller.simple_llm_response(query)
    print(query_response)
    controller.json_retriever.qdr_client.close()

if __name__ == "__main__":
   

    embedding_creation(vec_dim=2560)
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

    



    
    

