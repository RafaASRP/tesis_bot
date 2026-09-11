import logging
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from backend.app.services.rag.ingestion import ingestion_pipeline

logger = logging.getLogger(__name__)


class RAGService:
    """
    Servicio de consulta y recuperación semántica de fragmentos normativos.
    Conecta el almacén vectorial con el motor conversacional de GovAssist Core.
    """

    def __init__(self):
        self._index: Optional[VectorStoreIndex] = None
        self._retriever: Optional[VectorIndexRetriever] = None
        self.top_k: int = 3

    def _ensure_initialized(self) -> None:
        """Garantiza la carga diferida del índice vectorial."""
        if self._index is None:
            logger.info("Inicializando índice vectorial en memoria de GovAssist Core...")
            self._index = ingestion_pipeline.run_ingestion()
            self._retriever = VectorIndexRetriever(
                index=self._index,
                similarity_top_k=self.top_k
            )

    def retrieve_context(self, query_str: str) -> List[Dict[str, Any]]:
        """
        Recupera los k nodos más relevantes para la consulta del usuario,
        retornando el texto, la fuente documental y la puntuación de similitud.
        """
        self._ensure_initialized()
        if not query_str or not query_str.strip():
            return []

        nodes: List[NodeWithScore] = self._retriever.retrieve(query_str)
        context_results: List[Dict[str, Any]] = []

        for item in nodes:
            metadata = item.node.metadata or {}
            context_results.append({
                "text": item.node.get_content(),
                "score": float(item.score) if item.score is not None else 0.0,
                "procedure": metadata.get("procedure", "general"),
                "source": metadata.get("filename", "normativa_oficial")
            })

        return context_results

    def get_formatted_context(self, query_str: str) -> str:
        """
        Genera un bloque de texto plano consolidado listo para inyectar
        en el system prompt del LLM o motor conversacional.
        """
        results = self.retrieve_context(query_str)
        if not results:
            return "No se encontró contexto normativo relevante."

        formatted_chunks = []
        for idx, item in enumerate(results, 1):
            source_tag = f"[{item['source']} - Similitud: {item['score']:.2f}]"
            formatted_chunks.append(f"--- Fragmento {idx} {source_tag} ---\n{item['text']}")

        return "\n\n".join(formatted_chunks)


# Singleton del servicio de recuperación RAG
rag_service = RAGService()
