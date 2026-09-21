import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class PlaywrightBaseEngine:
    """
    Motor base para agentes RPA optimizado para macOS Monterey.
    Utiliza instancias efímeras de Chromium sin banderas de sandbox de Linux
    para evitar banners de advertencia y bloqueos en el hilo del DOM.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def init_browser(self) -> Browser:
        """Inicializa Google Chrome con argumentos estrictos para macOS."""
        if not self._playwright:
            self._playwright = await async_playwright().start()

        if not self._browser:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--window-position=0,0",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            try:
                self._browser = await self._playwright.chromium.launch(
                    channel="chrome",
                    headless=self.headless,
                    args=launch_args
                )
            except Exception:
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )

        return self._browser

    async def create_stealth_page(self) -> Page:
        """Crea un contexto aislado con huella nativa de macOS."""
        browser = await self.init_browser()
        self._context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="es-MX",
            timezone_id="America/Mexico_City"
        )

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['es-MX', 'es', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

        return await self._context.new_page()

    async def close_browser(self):
        """Cierre ordenado de recursos de Playwright."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
