import os
import json
import csv
import logging
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Configuración del logger para monitorear el proceso de extracción
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("govassist-exporter")

# Carga de variables de entorno desde la raíz del backend
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def export_telemetry_data():
    """Extrae las métricas cuantitativas y evaluaciones SUS para análisis inferencial en SPSS/Python."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Credenciales de Supabase ausentes. Verifica el archivo .env en tu backend.")
        return

    # Inicialización del cliente singleton de Supabase
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
    
    tables = ["telemetry_metrics", "sus_evaluations"]

    for table in tables:
        try:
            logger.info(f"Iniciando extracción de la tabla: {table}...")
            # Solicitud de todos los registros para la evaluación cuasi-experimental
            response = client.table(table).select("*").execute()
            data = response.data

            if not data:
                logger.warning(f"La tabla {table} está vacía. No se generaron archivos.")
                continue

            # Exportación a formato JSON (ideal para ingesta en Python/Pandas)
            json_path = os.path.join(export_dir, f"{table}_{timestamp}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Exportación a formato CSV (ideal para importación directa en IBM SPSS)
            csv_path = os.path.join(export_dir, f"{table}_{timestamp}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"Extracción exitosa. Archivos listos en {export_dir}:")
            logger.info(f" -> {os.path.basename(json_path)}")
            logger.info(f" -> {os.path.basename(csv_path)}")

        except Exception as e:
            logger.error(f"Fallo en la conexión o extracción de {table}: {str(e)}")

if __name__ == "__main__":
    export_telemetry_data()
