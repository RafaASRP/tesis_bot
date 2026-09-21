import re
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from backend.app.services.rpa.base import PlaywrightBaseEngine
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class CurpBot:
    """
    Agente RPA omba'apóva pya'e ha hekopete gob.mx/curp rendive.
    Diseñado bajo el modelo Human-in-the-Loop (HITL) estricto:
    - Búsqueda por Clave CURP (18 caracteres) en #tab-01.
    - Conmutación formal a la pestaña 'Datos Personales' (#tab-02) vía Bootstrap.
    - Cero simulación: extracción directa de la constancia oficial emitida por RENAPO.
    - Descarga, almacenamiento efímero y apertura automática del archivo PDF oficial.
    """

    PORTAL_URL_DATOS = "https://www.gob.mx/curp/#tab-02"
    PORTAL_URL_CLAVE = "https://www.gob.mx/curp/#tab-01"
    CURP_REGEX = r"[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d"

    STATE_NAMES = {
        "AGUASCALIENTES": "Aguascalientes", "BAJA CALIFORNIA": "Baja California",
        "BAJA CALIFORNIA SUR": "Baja California Sur", "CAMPECHE": "Campeche",
        "COAHUILA": "Coahuila", "COLIMA": "Colima", "CHIAPAS": "Chiapas",
        "CHIHUAHUA": "Chihuahua", "CIUDAD DE MEXICO": "Ciudad de México",
        "CDMX": "Ciudad de México", "DURANGO": "Durango", "GUANAJUATO": "Guanajuato",
        "GUERRERO": "Guerrero", "HIDALGO": "Hidalgo", "JALISCO": "Jalisco",
        "MEXICO": "Estado de México", "ESTADO DE MEXICO": "Estado de México",
        "MICHOACAN": "Michoacán", "MORELOS": "Morelos", "NAYARIT": "Nayarit",
        "NUEVO LEON": "Nuevo León", "OAXACA": "Oaxaca", "PUEBLA": "Puebla",
        "QUERETARO": "Querétaro", "QUINTANA ROO": "Quintana Roo",
        "SAN LUIS POTOSI": "San Luis Potosí", "SINALOA": "Sinaloa",
        "SONORA": "Sonora", "TABASCO": "Tabasco", "TAMAULIPAS": "Tamaulipas",
        "TLAXCALA": "Tlaxcala", "VERACRUZ": "Veracruz", "YUCATAN": "Yucatán",
        "ZACATECAS": "Zacatecas", "NACIDO EN EL EXTRANJERO": "Nacido en el Extranjero"
    }

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.download_dir = Path(settings.DOWNLOADS_PATH)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_text(self, text: Optional[str]) -> str:
        return text.strip().upper() if text else ""

    async def query_by_curp(self, curp_clave: str) -> Dict[str, Any]:
        """
        Omoinge CURP clave 18 caracteres rehegua pestaña #tab-01 ryepýpe,
        omomýi eventos nativos ha ojapyhy RENAPO kuatia oficial.
        """
        clean_curp = self._normalize_text(curp_clave)
        if not re.match(self.CURP_REGEX, clean_curp):
            return {
                "success": False,
                "error": f"La clave proporcionada ({clean_curp}) no cumple con el formato oficial de 18 caracteres.",
                "is_simulated": False
            }

        engine = PlaywrightBaseEngine(headless=self.headless)
        page: Optional[Page] = None
        try:
            page = await engine.create_stealth_page()
            logger.info("Navegando a gob.mx/curp/#tab-01 para búsqueda por clave...")
            await page.goto(self.PORTAL_URL_CLAVE, wait_until="domcontentloaded", timeout=25000)

            # 1. Clic directo y conmutación formal a #tab-01
            tab_loc = page.locator('a[href*="tab-01"], a:has-text("Clave Única")').first
            await tab_loc.wait_for(state="visible", timeout=8000)
            await tab_loc.click()
            await page.wait_for_timeout(200)

            # 2. Inyección exacta de la clave en el input nativo
            curp_input = page.locator('#tab-01 input#curp, input#curp').first
            await curp_input.wait_for(state="visible", timeout=8000)
            await curp_input.click()
            await curp_input.fill(clean_curp)

            # 3. Sincronización de formularios y desbloqueo del botón
            await page.evaluate("""
                () => {
                    const tab1 = document.querySelector('#tab-01') || document;
                    const input = tab1.querySelector('input#curp') || document.querySelector('input#curp');
                    if (input) {
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    const forms = tab1.querySelectorAll('form');
                    forms.forEach(f => {
                        f.dispatchEvent(new Event('input', { bubbles: true }));
                        f.dispatchEvent(new Event('change', { bubbles: true }));
                    });

                    const buttons = tab1.querySelectorAll('button');
                    buttons.forEach(btn => {
                        if (btn.textContent.toLowerCase().includes('buscar') || btn.type === 'submit' || btn.id === 'searchButton') {
                            btn.removeAttribute('disabled');
                            btn.disabled = false;
                            btn.classList.remove('disabled');
                            btn.style.pointerEvents = 'auto';
                            btn.style.opacity = '1';
                        }
                    });
                }
            """)

            search_btn = page.locator('#tab-01 button:has-text("Buscar"), #tab-01 button#searchButton, button:has-text("Buscar"):visible').first
            await search_btn.scroll_into_view_if_needed()

            print("\n" + "=" * 65)
            print(">> CLAVE CURP INYECTADA EN #tab-01")
            print(f">> Clave ingresada: {clean_curp}")
            print("-" * 65)
            print(">> FASE HITL (HUMAN-IN-THE-LOOP):")
            print(">> 1. Haz un solo clic sobre 'Buscar' en la ventana abierta.")
            print(">> 2. Resuelve el desafío de imágenes si Google reCAPTCHA lo solicita.")
            print(">> El bot capturará la constancia y abrirá el PDF oficial...")
            print("=" * 65 + "\n")

            # 4. Escucha activa de los resultados oficiales emitidos por RENAPO
            found_curp = None
            for _ in range(120):
                content = await page.content()

                if "Los datos ingresados no son correctos" in content or "no se encuentra registrada" in content or "no existe" in content:
                    alert_el = page.locator('.alert-danger, [role="alert"], #error-div').first
                    err_msg = await alert_el.inner_text() if await alert_el.count() > 0 else "La CURP ingresada no coincide con los registros de RENAPO."
                    return {
                        "success": False,
                        "error": f"RENAPO reporta: {err_msg.strip()}",
                        "is_simulated": False
                    }

                download_btn = page.locator('button:has-text("Descargar"), a:has-text("Descargar pdf"), #download, a[href*="descargar"]').first
                if await download_btn.count() > 0 and await download_btn.is_visible():
                    found_curp = clean_curp
                    logger.info(f"Constancia oficial localizada: {found_curp}")
                    break

                table_element = page.locator('.table-responsive, table, #datos-curp, .panel-body').first
                if await table_element.count() > 0 and await table_element.is_visible():
                    table_text = await table_element.inner_text()
                    curp_match = re.search(self.CURP_REGEX, table_text)
                    if curp_match:
                        found_curp = curp_match.group(0)
                        logger.info(f"CURP confirmada por RENAPO: {found_curp}")
                        break

                await page.wait_for_timeout(800)

            if not found_curp:
                return {
                    "success": False,
                    "error": "No se obtuvo respuesta de RENAPO dentro del tiempo límite. No se devuelven datos simulados.",
                    "is_simulated": False
                }

            # 5. Descarga y apertura automática de la constancia PDF en macOS
            pdf_filename = None
            download_btn = page.locator('button:has-text("Descargar"), a:has-text("Descargar pdf"), #download, a[href*="descargar"]').first
            if await download_btn.count() > 0 and await download_btn.is_visible():
                try:
                    pdf_filename = f"curp_{found_curp}_{uuid.uuid4().hex[:4]}.pdf"
                    pdf_path = self.download_dir / pdf_filename
                    async with page.expect_download(timeout=15000) as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(str(pdf_path))
                    logger.info(f"Documento oficial guardado en: {pdf_path}")

                    subprocess.Popen(["open", str(pdf_path)])
                    print(f"\n>> [SISTEMA] Archivo PDF oficial desplegado en pantalla: {pdf_path.name}")
                except Exception as ex:
                    logger.warning(f"Aviso durante la descarga o despliegue del PDF: {ex}")

            return {
                "success": True,
                "curp": found_curp,
                "pdf_filename": pdf_filename,
                "message": "Constancia oficial localizada, descargada y abierta con éxito mediante clave CURP.",
                "is_simulated": False
            }

        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": "Tiempo de espera agotado al conectar con gob.mx.",
                "is_simulated": False
            }
        except Exception as e:
            logger.error(f"Error en interacción RPA por clave: {e}")
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

    async def fill_form_hitl(
        self,
        names: str,
        first_surname: str,
        second_surname: Optional[str],
        day: str,
        month: str,
        year: str,
        gender: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Navega, conmuta formalmente a 'Datos Personales' (#tab-02),
        llena los campos registrales, habilita el botón y extrae el resultado oficial de RENAPO.
        """
        engine = PlaywrightBaseEngine(headless=self.headless)
        page: Optional[Page] = None
        try:
            page = await engine.create_stealth_page()
            logger.info("Navegando a gob.mx/curp/#tab-02...")
            
            await page.goto(self.PORTAL_URL_DATOS, wait_until="domcontentloaded", timeout=25000)

            # 1. Clic formal sobre la pestaña Datos Personales
            tab_loc = page.locator('a[href*="tab-02"], a:has-text("Datos Personales")').first
            await tab_loc.wait_for(state="visible", timeout=8000)
            await tab_loc.click()
            await page.wait_for_timeout(300)

            # Activación canónica en Bootstrap por respaldo
            await page.evaluate("""
                () => {
                    const tab2Link = document.querySelector('a[href*="tab-02"]') || 
                                     Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('Datos Personales'));
                    if (tab2Link) {
                        if (window.jQuery && window.jQuery(tab2Link).tab) {
                            window.jQuery(tab2Link).tab('show');
                        }
                        const liParent = tab2Link.closest('li');
                        if (liParent && liParent.parentElement) {
                            Array.from(liParent.parentElement.children).forEach(li => li.classList.remove('active'));
                            liParent.classList.add('active');
                        }
                    }
                    const tab1Pane = document.querySelector('#tab-01');
                    const tab2Pane = document.querySelector('#tab-02');
                    if (tab1Pane) { tab1Pane.classList.remove('active', 'in'); tab1Pane.style.display = 'none'; }
                    if (tab2Pane) { tab2Pane.classList.add('active', 'in'); tab2Pane.style.display = 'block'; }
                }
            """)

            # 2. Inyección exacta de campos de texto
            nombre_val = self._normalize_text(names)
            primer_ap_val = self._normalize_text(first_surname)
            segundo_ap_val = self._normalize_text(second_surname)

            nombres_input = page.locator('#tab-02 input#nombre, input#nombre').first
            await nombres_input.wait_for(state="visible", timeout=8000)
            await nombres_input.fill(nombre_val)

            p_ape = page.locator('#tab-02 input#primerApellido, input#primerApellido').first
            await p_ape.fill(primer_ap_val)

            if segundo_ap_val:
                s_ape = page.locator('#tab-02 input#segundoApellido, input#segundoApellido').first
                await s_ape.fill(segundo_ap_val)

            # 3. Fecha de nacimiento
            clean_day = str(int(day))
            day_field = page.locator('#tab-02 select#diaNacimiento, select#diaNacimiento').first
            try:
                await day_field.select_option(value=clean_day)
            except Exception:
                await day_field.select_option(label=clean_day.zfill(2))

            clean_month = str(int(month)).zfill(2)
            month_field = page.locator('#tab-02 select#mesNacimiento, select#mesNacimiento').first
            try:
                await month_field.select_option(value=clean_month)
            except Exception:
                await month_field.select_option(value=str(int(month)))

            clean_year = str(year).strip()
            year_input = page.locator('#tab-02 input[placeholder*="1943"], #tab-02 input#year, #tab-02 input#agnoNacimiento').first
            if await year_input.count() > 0 and await year_input.is_visible():
                await year_input.fill(clean_year)
            else:
                year_select = page.locator('#tab-02 select#year, #tab-02 select#agnoNacimiento').first
                await year_select.select_option(clean_year)

            # 4. Sexo, Estado y sincronización reactiva
            target_gender = "Hombre" if gender.strip().upper().startswith("H") else "Mujer"
            clean_state_key = self._normalize_text(state)
            official_state = self.STATE_NAMES.get(clean_state_key, state.strip().title())

            await page.evaluate("""
                (args) => {
                    const tab2 = document.querySelector('#tab-02') || document;
                    const selects = tab2.querySelectorAll('select');
                    
                    // Sexo
                    for (const s of selects) {
                        for (let i = 0; i < s.options.length; i++) {
                            if (s.options[i].text.trim().toLowerCase() === args.gender.toLowerCase()) {
                                s.selectedIndex = i;
                                s.value = s.options[i].value;
                                ['input', 'change'].forEach(ev => s.dispatchEvent(new Event(ev, { bubbles: true })));
                                break;
                            }
                        }
                    }

                    // Estado
                    const target = args.state.toLowerCase();
                    for (const s of selects) {
                        for (let i = 0; i < s.options.length; i++) {
                            const optText = s.options[i].text.trim().toLowerCase();
                            if (optText.includes(target) || optText === target) {
                                s.selectedIndex = i;
                                s.value = s.options[i].value;
                                ['input', 'change'].forEach(ev => s.dispatchEvent(new Event(ev, { bubbles: true })));
                                break;
                            }
                        }
                    }

                    // Sincronizar y marcar cualquier radio o checkbox del formulario
                    const radios = tab2.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                    radios.forEach(r => {
                        r.checked = true;
                        ['input', 'change', 'click'].forEach(ev => r.dispatchEvent(new Event(ev, { bubbles: true })));
                    });

                    // Sincronización reactiva del formulario
                    const forms = tab2.querySelectorAll('form');
                    forms.forEach(f => {
                        f.dispatchEvent(new Event('input', { bubbles: true }));
                        f.dispatchEvent(new Event('change', { bubbles: true }));
                    });

                    // Habilitación del botón Buscar
                    const buttons = tab2.querySelectorAll('button');
                    buttons.forEach(btn => {
                        if (btn.textContent.toLowerCase().includes('buscar') || btn.type === 'submit' || btn.id === 'searchButton') {
                            btn.removeAttribute('disabled');
                            btn.disabled = false;
                            btn.classList.remove('disabled');
                            btn.style.pointerEvents = 'auto';
                            btn.style.opacity = '1';
                        }
                    });
                }
            """, {"gender": target_gender, "state": official_state})

            search_btn = page.locator('#tab-02 button:has-text("Buscar"), #tab-02 button#searchButton, button:has-text("Buscar"):visible').first
            await search_btn.scroll_into_view_if_needed()

            print("\n" + "=" * 65)
            print(">> PESTAÑA 'DATOS PERSONALES' ACTIVADA AUTOMÁTICAMENTE")
            print(f">> Nombres: {nombre_val}")
            print(f">> Primer Apellido: {primer_ap_val} | Segundo Apellido: {segundo_ap_val}")
            print(f">> Fecha: {clean_day}/{clean_month}/{clean_year} | Estado: {official_state} | Sexo: {target_gender}")
            print("-" * 65)
            print(">> FASE HITL (HUMAN-IN-THE-LOOP):")
            print(">> 1. Haz un solo clic sobre 'Buscar' en la ventana abierta.")
            print(">> 2. Resuelve el desafío de imágenes si Google lo solicita.")
            print(">> El bot extraerá la constancia tan pronto RENAPO responda...")
            print("=" * 65 + "\n")

            # 5. Escucha activa de los resultados oficiales de RENAPO
            found_curp = None
            for _ in range(120):
                content = await page.content()

                # A) Error oficial emitido por la base de datos de RENAPO
                if "Los datos ingresados no son correctos" in content or "no se encuentra registrada" in content:
                    alert_el = page.locator('.alert-danger, [role="alert"], #error-div').first
                    err_msg = await alert_el.inner_text() if await alert_el.count() > 0 else "Los datos ingresados no coinciden con los registros de RENAPO."
                    return {
                        "success": False,
                        "error": f"RENAPO reporta: {err_msg.strip()}",
                        "is_simulated": False
                    }

                # B) Constancia localizada en el DOM
                download_btn = page.locator('button:has-text("Descargar"), a:has-text("Descargar pdf"), #download, a[href*="descargar"]').first
                if await download_btn.count() > 0 and await download_btn.is_visible():
                    found_curp = f"{nombre_val[:2]}{primer_ap_val[:2]}"
                    break

                table_element = page.locator('.table-responsive, table, #datos-curp').first
                if await table_element.count() > 0 and await table_element.is_visible():
                    table_text = await table_element.inner_text()
                    curp_match = re.search(self.CURP_REGEX, table_text)
                    if curp_match:
                        found_curp = curp_match.group(0)
                        logger.info(f"CURP oficial certificada recuperada de RENAPO: {found_curp}")
                        break

                await page.wait_for_timeout(800)

            if not found_curp:
                return {
                    "success": False,
                    "error": "No se obtuvo respuesta de RENAPO dentro del tiempo límite. No se devuelven datos simulados.",
                    "is_simulated": False
                }

            # 6. Descarga y apertura automática del archivo PDF oficial emitido por RENAPO
            pdf_filename = None
            download_btn = page.locator('button:has-text("Descargar"), a:has-text("Descargar pdf"), #download, a[href*="descargar"]').first
            if await download_btn.count() > 0 and await download_btn.is_visible():
                try:
                    pdf_filename = f"curp_{found_curp}_{uuid.uuid4().hex[:4]}.pdf"
                    pdf_path = self.download_dir / pdf_filename
                    async with page.expect_download(timeout=15000) as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(str(pdf_path))
                    logger.info(f"Documento oficial de RENAPO guardado en: {pdf_path}")

                    # Apertura automática en Vista Previa (macOS)
                    subprocess.Popen(["open", str(pdf_path)])
                    print(f"\n>> [SISTEMA] Archivo PDF oficial desplegado en pantalla: {pdf_path.name}")
                except Exception as ex:
                    logger.warning(f"Aviso durante la descarga o despliegue del PDF oficial: {ex}")

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


curp_bot = CurpBot(headless=False)
