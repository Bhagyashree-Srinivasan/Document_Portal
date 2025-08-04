import os
import sys
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from utils.config_loader import load_config
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)

class ModelLoader:
    """
    A utility class to load embedding models and LLM models
    """

    def __init__(self):

        load_dotenv()
        self._validate_env()
        self.config = load_config()
        log.info("Configuration loaded successfully", config_keys=list(self.config.keys()))

    def _validate_env(self):
        """
        Validate the necessary environment variables for model loading.
        """
        required_vars = ['GOOGLE_API_KEY', 'GROQ_API_KEY']
        self.api_keys = {key: os.getenv(key) for key in required_vars}

        missing_vars = [key for key, value in self.api_keys.items() if not value]
        if missing_vars:
            log.error(f"Missing environment variables", missing_vars=missing_vars)
            raise DocumentPortalException("Missing required environment variables", sys)
        
        log.info("environment variables validated successfully", available_keys=list(key for key in self.api_keys.keys() if self.api_keys[key]))

    def load_embedding(self):
        """
        Load and return the embedding model.
        """
        try:
            log.info("Loading embedding model....")
            model_name = self.config["embedding_model"]["model_name"]
            return GoogleGenerativeAI(model = model_name)
        except Exception as e:
            log.error("Failed to load embedding model", error=str(e))
            raise DocumentPortalException("Failed to load embedding model", sys)

    def load_llm(self):
        """
        Load and return the LLM model.
        Loads LLM dynamically based on provider in config.
        """
        llm_block = self.config['llm']
        
        #Default provider or choose from the ENV var
        provider_key = os.getenv("LLM_PROVIDER", 'groq') #Default groq; Set the provider in env file.

        if provider_key not in llm_block:
            log.error("LLM provider not found in config", provider_key = provider_key)
            raise ValueError(f"LLM provider '{provider_key}' not found in config")
        
        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_tokens", 2048)

        log.info("Loading LLM model", provider=provider, model_name=model_name,
                 temperature=temperature, max_tokens=max_tokens)
        
        if provider == 'google':
            llm = ChatGoogleGenerativeAI(
                model = model_name,
                api_key = self.api_keys['GOOGLE_API_KEY'],
                temperature=temperature,
            )
            return llm
        
        elif provider == 'groq':
            llm = ChatGroq(
                model = model_name,
                api_key = self.api_keys['GROQ_API_KEY'],
                temperature = temperature,
            )
            return llm 

        elif provider == 'openai':
            llm = ChatOpenAI(
                model_name = model_name,
                api_key = self.api_keys["OPENAI_API_KEY"],
                temperature = temperature,
                max_tokens = max_tokens
            )
            return llm
        
        else:
            log.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
if __name__ == "__main__":
    loader = ModelLoader()

    #Test embedding model loading
    embeddings = loader.load_embedding()
    print("Embedding model loaded successfully: ", embeddings)

    #Test LLM model loading
    llm = loader.load_llm()
    print("LLM model loaded successfully: ", llm)

    #Test the ModelLoader
    result = llm.invoke("Hello, how are you?")
    print("LLM response: ", result.content)
