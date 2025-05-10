import sys
sys.path.append("../")
from transformers import AutoModel, AutoTokenizer
from transformers.utils import hub
from functools import partial
from bw_utils import get_child_folders
import torch
import os


class EmbeddingModel:
    def __init__(self, model_name, language='en'):
        self.model_name = model_name
        self.language = language
        cache_dir = hub.default_cache_path
        model_provider = model_name.split("/")[0]
        model_smallname = model_name.split("/")[1]
        model_path = os.path.join(cache_dir, f"models--{model_provider}--{model_smallname}/snapshots/")
        if os.path.exists(model_path) and get_child_folders(model_path):
            try:
                model_path = os.path.join(model_path,get_child_folders(model_path)[0])
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModel.from_pretrained(model_path)
            except Exception as e:
                print(e)
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModel.from_pretrained(model_name)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)

    def __call__(self, input):
        inputs = self.tokenizer(input, return_tensors="pt", padding=True, truncation=True, max_length=256)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state[:, 0, :].tolist()
        return embeddings

class OpenAIEmbedding:
    def __init__(self, model_name="text-embedding-ada-002"):
        from openai import OpenAI
        self.client = OpenAI()
        self.model_name = model_name

    def __call__(self, input):
        if isinstance(input, str):
            input = input.replace("\n", " ")
            return self.client.embeddings.create(input=[input], model=self.model_name).data[0].embedding
        elif isinstance(input,list):
            return [self.client.embeddings.create(input=[sentence.replace("\n", " ")], model=self.model_name).data[0].embedding for sentence in input]

def get_embedding_model(embed_name, language='en'):
    model_name_dict = {
        "bge-m3":"BAAI/bge-m3",
        "bge": "BAAI/bge-large-",
        "luotuo": "silk-road/luotuo-bert-medium",
        "bert": "google-bert/bert-base-multilingual-cased",
    }
    
    if embed_name in model_name_dict:
        model_name = model_name_dict[embed_name]
        if embed_name == 'bge':
            model_name += language
        return EmbeddingModel(model_name)
    else:
        return OpenAIEmbedding()

