import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page
)
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class PlaywrightBaseEngine:
    """
    Motor base de automatización robótica (RPA) con Playwright.
    Configurado con mitigación pasiva de huella digital (Stealth)
    para interactuar con el DOM público de portales federales (gob.mx).
    """

    STEALTH_INIT_SCRIPT = """
    // 1. Ocultar presencia de automatización WebDriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 2. Simular plugins estándar de navegador de escritorio
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // 3. Simular idiomas regionales de México
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-MX', 'es', 'en-US', 'en']
    });

    // 4. Parchear WebGL Vendor para evitar detección de hardware virtualizado
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris Pro Graphics 6200';
        }
        return getParameter.apply(this, [parameter]);
    };
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.download_dir = Path(settings.DOWNLOADS_PATH)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start_browser(self) -> Browser:
        """Inicia el proceso de Playwright y levanta la instancia de Chromium."""
        if not self._playwright:
            self._playwright = await async_playwright().start()

        if not self._browser:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            )
            logger.info("Instancia de Chromium iniciada exitosamente con flags de mitigación.")

        return self._browser

    async def create_stealth_context(self) -> BrowserContext:
        """Crea un contexto de navegación aislado con configuración de evasión pasiva."""
        browser = await self.start_browser()
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-MX",
            timezone_id="America/Mexico_City",
            accept_downloads=True
        )

        # Inyectar script de mitigación de huella antes de cualquier navegación
        await context.add_init_script(self.STEALTH_INIT_SCRIPT)
        return context

    async def create_stealth_page(self) -> Page:
        """Genera una página lista para interactuar con selectores gubernamentales."""
        context = await self.create_stealth_context()
        page = await context.new_page()
        page.set_default_timeout(30000)  # 30 segundos de timeout de red
        return page

    async def close_browser(self) -> None:
        """Libera los recursos del navegador y detiene el runtime de Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Motor Playwright cerrado y memoria liberada.")
