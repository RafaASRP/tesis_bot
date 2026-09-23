import re
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from app.services.rpa.base import PlaywrightBaseEngine
from app.core.config import settings

logger = logging.getLogger(__name__)


class CurpClaveBot:
    """
    Agente RPA aislado para la consulta de CURP mediante Clave Alfanumérica.
    
    Arquitectura Definitiva:
    - Sin interrupciones de red (preserva callbacks de reCAPTCHA y PDF).
    - Inyección por portapapeles de hardware (insert_text) para eludir los
      bloqueos reactivos de Ember.js.
    - Extracción automatizada del PDF y despliegue en macOS.
    """

    PORTAL_URL = "https://www.gob.mx/curp/"
    CURP_REGEX = r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$"

    def __init__(self, headless: bool = False):
        self.headless = headless
        # Almacén efímero de PDFs tramitados conforme a la arquitectura del monorepo
        self.download_dir = Path(settings.DOWNLOADS_PATH)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_curp(self, curp: Optional[str]) -> str:
        return curp.strip().upper() if curp else ""

    async def execute_query(self, curp_clave: str) -> Dict[str, Any]:
        clean_curp = self._normalize_curp(curp_clave)
        if not re.match(self.CURP_REGEX, clean_curp):
            return {
                "success": False,
                "error": f"La clave '{clean_curp}' no cumple con el formato de 18 caracteres.",
                "is_simulated": False
            }

        engine = PlaywrightBaseEngine(headless=self.headless)
        page: Optional[Page] = None
        try:
            page = await engine.create_stealth_page()
            logger.info("Navegando a gob.mx/curp/...")
            
            # Navegación sin abortar la red para no romper reCAPTCHA
            try:
                await page.goto(self.PORTAL_URL, wait_until="commit", timeout=20000)
            except Exception:
                pass

            # 1. Espera nativa del campo interactivo
            curp_input = page.locator('input#curp').first
            await curp_input.wait_for(state="visible", timeout=25000)
            
            # Dar tiempo a Ember.js para adjuntar sus Listeners internos
            await page.wait_for_timeout(1000)

            # 2. Inyección infalible a nivel OS (Portapapeles/Hardware)
            await curp_input.click()
            await page.keyboard.press("Meta+A")
            await page.keyboard.press("Backspace")
            
            # Simula Cmd+V directo del OS, desencadenando todos los eventos nativos
            await page.keyboard.insert_text(clean_curp)
            await page.keyboard.press("Tab")
            
            # Habilitación visual del botón Buscar
            await page.evaluate("""
                () => {
                    const btn = document.getElementById('searchButton');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.disabled = false;
                    }
                }
            """)

            print("\n" + "=" * 65)
            print(">> [MÓDULO CLAVE] INYECCIÓN POR HARDWARE COMPLETADA")
            print(f">> Clave ingresada: {clean_curp}")
            print("-" * 65)
            print(">> FASE HITL (HUMAN-IN-THE-LOOP):")
            print(">> 1. Haz un solo clic sobre 'Buscar' y resuelve el reCAPTCHA.")
            print(">> 2. NO DESCARGUES EL DOCUMENTO MANUALMENTE. Deja que el bot lo intercepte.")
            print("=" * 65 + "\n")

            # 3. Escucha activa de los resultados
            found_curp = None
            download_btn = page.locator('a#download').first
            
            for _ in range(150): # Espera HITL de hasta 2.5 minutos
                content = await page.content()

                if "Los datos ingresados no son correctos" in content or "no se encuentra registrada" in content:
                    alert_el = page.locator('.alert-danger, #error-div').first
                    err_msg = await alert_el.inner_text() if await alert_el.count() > 0 else "La CURP ingresada no coincide con los registros de RENAPO."
                    return {
                        "success": False,
                        "error": f"RENAPO reporta: {err_msg.strip()}",
                        "is_simulated": False
                    }

                # Detección estricta del ID del botón de descarga oficial
                if await download_btn.count() > 0 and await download_btn.is_visible():
                    found_curp = clean_curp
                    logger.info(f"Botón de descarga localizado para: {found_curp}")
                    break

                await page.wait_for_timeout(1000)

            if not found_curp:
                return {
                    "success": False,
                    "error": "No se obtuvo respuesta de RENAPO dentro del tiempo límite.",
                    "is_simulated": False
                }

            # 4. Descarga controlada y apertura automática
            pdf_filename = f"curp_{found_curp}_{uuid.uuid4().hex[:4]}.pdf"
            pdf_path = self.download_dir / pdf_filename
            
            try:
                # El bot captura el Blob en red sin fallos
                async with page.expect_download(timeout=20000) as download_info:
                    await download_btn.click(force=True)
                
                download = await download_info.value
                await download.save_as(str(pdf_path))
                logger.info(f"Documento oficial de RENAPO guardado en: {pdf_path}")

                subprocess.Popen(["open", str(pdf_path)])
                print(f"\n>> [SISTEMA] Archivo PDF oficial desplegado en pantalla: {pdf_path.name}")
            except Exception as ex:
                logger.warning(f"Error al interceptar el PDF: {ex}")
                return {
                    "success": False,
                    "error": f"Fallo en la descarga del PDF: {ex}",
                    "is_simulated": False
                }

            return {
                "success": True,
                "curp": found_curp,
                "pdf_filename": pdf_filename,
                "message": "Constancia oficial localizada, descargada y abierta con éxito.",
                "is_simulated": False
            }

        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": "Tiempo de espera agotado al conectar con gob.mx.",
                "is_simulated": False
            }
        except Exception as e:
            logger.error(f"Error en interacción RPA: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_simulated": False
            }
        finally:
            if page:
                try:
                    await page.context.browser.close()
                except Exception:
                    pass
            await engine.close_browser()


curp_clave_bot = CurpClaveBot(headless=False)
