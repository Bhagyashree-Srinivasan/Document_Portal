import sys
import os
from operator import itemgetter
from typing import Optional, List

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from prompts.prompt_library import PROMPT_REGISTRY
from model.models import PromptType


class ConversationRAG:
    def __init__(self, session_id: str, retriever=None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.session_id = session_id
            self.llm = ModelLoader().load_llm()
            self.contextualize_prompt = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROMPT_REGISTRY[PromptType.CONTEXT_QA.value]
            if retriever is None:
                raise ValueError("Retriever cannot be None")
            self.retriever = retriever
            self._build_lcel_chain()
            self.log.info("Conversation RAG initialized", session_id=session_id)

        except Exception as e:
            self.log.error(f"Failed to initialize ConversationRAG", error=str(e))
            raise DocumentPortalException("Initialization error in ConversationRAG", sys)
        

    def load_retriever_from_faiss(self, index_path: str):
        """
        Load a FAISS vectorstore from disk and convert to retriever.
        """
        try:
            embeddings = ModelLoader().load_embeddings()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"Index path {index_path} does not exist.")
            
            vectorstore = FAISS.load_local(
                index_path,
                embeddings,
                allow_dangerous_deserialization= True # Only use this if you trust the source of the index
            )

            self.retriever = vectorstore.as_retriever(search_type = "similarity", search_kwargs = {"k": 5})
            self.log.info("Retriever loaded from FAISS", index_path=index_path, session_id=self.session_id)
            return self.retriever
        except Exception as e:
            self.log.error(f"Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException("Error loading retriever from FAISS", sys)
    
    def invoke(self, user_input: str, chat_history: Optional[list[BaseMessage]] = None) -> str:
        try:
            chat_history = chat_history or []
            payload = {
                "input": user_input,
                "chat_history": chat_history
            }
            answer = self.chain.invoke(payload)
            if not answer:
                self.log.warning("No answer generated", user_input = user_input, session_id=self.session_id)
                return "No answer generated"
            self.log.info("Answer generated successfully", user_input=user_input, session_id=self.session_id, answer_preview=answer[:100])
            return answer
        except Exception as e:
            self.log.error(f"Error invoking ConversationRAG", error=str(e))
            raise DocumentPortalException("Error invoking ConversationRAG", sys)

    def _load_llm(self):
        try:
            llm  = ModelLoader().load_llm()
            if not llm:
                raise ValueError("LLM could not be loaded")
            self.log.info("LLM loaded successfully", class_name=llm.__class__.__name__, session_id = self.session_id)
        except Exception as e:
            self.log.error(f"Failed to load LLM", error=str(e))
            raise DocumentPortalException("Error during LLM loading", sys)

    @staticmethod
    def _format_docs(docs):
        return "\n\n".join(
            d.page_content 
            for d in docs
        )

    def _build_lcel_chain(self):
        try:
            #1. Rewrite question using chat history
            question_rewriter = (
                {"input": itemgetter("input"), "chat_history": itemgetter("chat_history")}
                | self.contextualize_prompt
                | self.llm
                | StrOutputParser()
            )

            #2. Retrieve docs for rewritten question
            retrieve_docs = question_rewriter| self.retriever | self._format_docs

            #3. Feed Context + Original input + chat history into answer prompt
            self.chain = (
                {
                    "context": retrieve_docs,
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | self.qa_prompt
                | self.llm
                | StrOutputParser()
            )
            self.log.info("LCEL chain built successfully", session_id=self.session_id)
        except Exception as e:
            self.log.error(f"Failed to build LCEL chain", error=str(e))
            raise DocumentPortalException("Error building LCEL chain", sys)
