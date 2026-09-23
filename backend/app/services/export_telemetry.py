import csv
import json
import logging
from pathlib import Path
from app.core.supabase import supabase
from app.api.v1.endpoints.telemetry import OFFLINE_TELEMETRY_TASKS, OFFLINE_TELEMETRY_SUS

logger = logging.getLogger(__name__)

class TelemetryExporter:
    """
    Exportador automatizado de datos cuantitativos de rendimiento y usabilidad (SUS)
    para el análisis estadístico cuasi-experimental de la tesis.
    """
    def __init__(self):
        self.export_dir = Path("data/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def export_to_csv(self):
        tasks_data = []
        sus_data = []

        if supabase:
            try:
                res_tasks = supabase.table("telemetry_tasks").select("*").execute()
                tasks_data = res_tasks.data or []
                res_sus = supabase.table("telemetry_sus").select("*").execute()
                sus_data = res_sus.data or []
            except Exception as e:
                logger.error(f"Error consultando Supabase para exportación: {e}")
        
        # Respaldo con datos locales si Supabase no está conectado
        if not tasks_data:
            tasks_data = OFFLINE_TELEMETRY_TASKS
        if not sus_data:
            sus_data = OFFLINE_TELEMETRY_SUS

        # 1. Exportar Tareas (Task Performance: T, E, L, S)
        tasks_file = self.export_dir / "telemetry_tasks_export.csv"
        if tasks_data:
            keys = tasks_data[0].keys()
            with open(tasks_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(tasks_data)
            print(f">> [EXPORTACIÓN] Tareas exportadas exitosamente a: {tasks_file}")
        else:
            print(">> [EXPORTACIÓN] No hay registros de telemetría de tareas disponibles.")

        # 2. Exportar Cuestionario SUS (Usabilidad)
        sus_file = self.export_dir / "telemetry_sus_export.csv"
        if sus_data:
            keys = sus_data[0].keys()
            with open(sus_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(sus_data)
            print(f">> [EXPORTACIÓN] Cuestionario SUS exportado exitosamente a: {sus_file}")
        else:
            print(">> [EXPORTACIÓN] No hay registros de cuestionarios SUS disponibles.")

    async def export_to_json(self):
        tasks_data = supabase.table("telemetry_tasks").select("*").execute().data if supabase else OFFLINE_TELEMETRY_TASKS
        sus_data = supabase.table("telemetry_sus").select("*").execute().data if supabase else OFFLINE_TELEMETRY_SUS

        combined = {
            "telemetry_tasks": tasks_data,
            "telemetry_sus": sus_data
        }

        json_file = self.export_dir / "gover_assist_complete_telemetry.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=4)
        print(f">> [EXPORTACIÓN] Dataset completo guardado en JSON: {json_file}")

if __name__ == "__main__":
    import asyncio
    exporter = TelemetryExporter()
    asyncio.run(exporter.export_to_csv())
    asyncio.run(exporter.export_to_json())
