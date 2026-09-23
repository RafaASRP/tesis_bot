import logging
from pathlib import Path
from typing import List, Tuple
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeIngestionPipeline:
    """
    Pipeline de ingesta e indexación de fichas normativas en Pinecone Serverless
    con fallback automático a almacenamiento vectorial en memoria local.
    """

    def __init__(self):
        # Modelo local multilingüe de 384 dimensiones optimizado para CPU/PyTorch
        self.embed_dim = 384
        self.embed_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self._setup_embedding_model()
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    def _setup_embedding_model(self) -> None:
        """Configura el modelo de embeddings en el runtime global de LlamaIndex."""
        logger.info(f"Cargando modelo de embeddings local: {self.embed_model_name}")
        self.embed_model = HuggingFaceEmbedding(model_name=self.embed_model_name)
        Settings.embed_model = self.embed_model

    def load_raw_documents(self) -> List[Document]:
        """Carga y etiqueta con metadatos las fichas normativas desde data/raw_docs/."""
        raw_path = Path(settings.RAW_DOCS_PATH)
        documents: List[Document] = []

        if not raw_path.exists():
            logger.error(f"Ruta de documentos no encontrada: {raw_path}")
            return documents

        for md_file in raw_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            doc = Document(
                text=content,
                metadata={
                    "filename": md_file.name,
                    "procedure": md_file.stem,
                    "source": "gob.mx_oficial"
                }
            )
            documents.append(doc)
            logger.info(f"Documento normativo cargado: {md_file.name}")

        return documents

    def _get_pinecone_vector_store(self) -> Tuple[PineconeVectorStore, bool]:
        """Inicializa el índice en Pinecone Serverless o conmuta a contingencia."""
        is_mock = "mock" in settings.PINECONE_API_KEY or "tu_pinecone" in settings.PINECONE_API_KEY
        if is_mock or not settings.PINECONE_API_KEY:
            logger.warning("Pinecone API Key no válida. Activando contingencia en memoria local.")
            return None, False

        try:
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            existing_indexes = [idx.name for idx in pc.list_indexes()]

            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(f"Creando índice serverless '{settings.PINECONE_INDEX_NAME}' en Pinecone...")
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=self.embed_dim,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.PINECONE_ENVIRONMENT)
                )

            pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
            vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
            return vector_store, True
        except Exception as e:
            logger.error(f"Fallo al conectar con Pinecone ({e}). Conmutando a modo contingencia local.")
            return None, False

    def run_ingestion(self) -> VectorStoreIndex:
        """Ejecuta el pipeline completo de carga, fragmentación e indexación."""
        docs = self.load_raw_documents()
        if not docs:
            raise ValueError("No se encontraron documentos normativos en data/raw_docs/")

        vector_store, is_remote = self._get_pinecone_vector_store()

        if is_remote and vector_store:
            from llama_index.core import StorageContext
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                docs,
                storage_context=storage_context,
                transformations=[self.node_parser]
            )
            logger.info("Ingesta completada exitosamente en Pinecone Serverless.")
            return index

        # Contingencia: Indexación local en memoria volátil
        index = VectorStoreIndex.from_documents(
            docs,
            transformations=[self.node_parser]
        )
        logger.info("Ingesta completada exitosamente en índice vectorial local (Memoria).")
        return index


ingestion_pipeline = KnowledgeIngestionPipeline()
