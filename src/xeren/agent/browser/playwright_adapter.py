"""Production-oriented Playwright Browser Adapter for Xeren Autonomous Work Agent."""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.errors import (
    BrowserActionError,
    BrowserAdapterError,
    BrowserElementNotFoundError,
    BrowserNavigationError,
    BrowserSecurityError,
    BrowserSessionError,
    BrowserTimeoutError,
)
from xeren.agent.browser.security import BrowserSecurityManager
from xeren.agent.types import ActionResult, BrowserError, BrowserObservation, InteractiveElement

logger = logging.getLogger("xeren.agent.browser.playwright")

# Optional Playwright import with graceful detection
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PlaywrightTimeoutError,
        async_playwright,
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeoutError = Exception  # type: ignore
    async_playwright = None  # type: ignore


class PlaywrightBrowserAdapter(BaseBrowserAdapter):
    """Production browser adapter utilizing Playwright with strict security boundaries and structured error handling."""

    def __init__(
        self,
        security_manager: Optional[BrowserSecurityManager] = None,
        headless: bool = True,
        browser_type: str = "chromium",
        default_timeout_ms: int = 30000,
        action_timeout_ms: int = 10000,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        page: Optional[Any] = None,  # Pre-injected Page for testing/mocks
    ) -> None:
        self.security = security_manager or BrowserSecurityManager()
        self.headless = headless
        self.browser_type_name = browser_type.lower()
        self.default_timeout_ms = default_timeout_ms
        self.action_timeout_ms = action_timeout_ms
        self.viewport = viewport or {"width": 1280, "height": 800}
        self.user_agent = user_agent

        # Internal state
        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None
        self._context: Optional[Any] = None
        self._page: Optional[Any] = page
        self._is_external_page = page is not None
        self._is_closed = False
        self._lock = asyncio.Lock()

    @property
    def page(self) -> Optional[Any]:
        """Active page instance."""
        return self._page

    @property
    def is_active(self) -> bool:
        """Whether adapter has an active browser session."""
        return self._page is not None and not self._is_closed

    async def ainitialize(self) -> None:
        """Initialize browser, context, and default page."""
        async with self._lock:
            if self._page is not None and not self._is_closed:
                return

            if (not PLAYWRIGHT_AVAILABLE or async_playwright is None) and not self._is_external_page:
                raise BrowserSessionError(
                    "Playwright library is not installed. Install with: pip install playwright && playwright install chromium",
                    recoverable=False,
                )

            try:
                if self._page is None:
                    assert async_playwright is not None
                    self._playwright = await async_playwright().start()
                    launcher = getattr(self._playwright, self.browser_type_name, None)
                    if launcher is None:
                        raise BrowserSessionError(
                            f"Unsupported browser type: {self.browser_type_name}. Supported: chromium, firefox, webkit",
                            recoverable=False,
                        )

                    self._browser = await launcher.launch(headless=self.headless)
                    if self._browser is None:
                        raise BrowserSessionError("Failed to start browser instance", recoverable=False)

                    context_kwargs: Dict[str, Any] = {
                        "viewport": self.viewport,
                        "accept_downloads": True,
                    }
                    if self.user_agent:
                        context_kwargs["user_agent"] = self.user_agent

                    self._context = await self._browser.new_context(**context_kwargs)
                    if self._context is None:
                        raise BrowserSessionError("Failed to create browser context", recoverable=False)
                    self._page = await self._context.new_page()

                # Configure timeouts on active page
                if self._page is not None and hasattr(self._page, "set_default_timeout"):
                    self._page.set_default_timeout(self.action_timeout_ms)
                if self._page is not None and hasattr(self._page, "set_default_navigation_timeout"):
                    self._page.set_default_navigation_timeout(self.default_timeout_ms)

                self._is_closed = False
                logger.info("Playwright browser adapter initialized successfully (%s)", self.browser_type_name)

            except Exception as err:
                await self._cleanup_resources()
                sanitized_msg = self.security.sanitize_text(str(err))
                raise BrowserSessionError(
                    f"Failed to launch browser session: {sanitized_msg}",
                    recoverable=False,
                    details={"error": sanitized_msg},
                ) from err

    async def anavigate(self, url: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Navigate to validated URL with structured timeout and error translation."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        timeout = timeout_ms or self.default_timeout_ms

        try:
            validated_url = self.security.validate_url(url)
            await self._ensure_active_page()

            assert self._page is not None
            logger.info("Navigating to: %s", validated_url)

            response = await self._page.goto(
                validated_url,
                timeout=timeout,
                wait_until="domcontentloaded",
            )

            status_code = response.status if response is not None else 200
            if status_code >= 400:
                logger.warning("HTTP status %d received for %s", status_code, validated_url)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={
                    "url": obs.url,
                    "title": obs.title,
                    "status_code": status_code,
                },
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except BrowserSecurityError as err:
            return self._build_failure_result(action_id, start, err.message, err.code, err.category, recoverable=False)
        except PlaywrightTimeoutError as err:
            safe_msg = f"Navigation to '{url}' timed out after {timeout}ms."
            return self._build_failure_result(action_id, start, safe_msg, "TIMEOUT", "timeout", recoverable=True)
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "NAVIGATION_FAILED"
            if "net::ERR_" in safe_err or "NS_ERROR_" in safe_err or "DNS" in safe_err:
                code = "NETWORK_ERROR"
            return self._build_failure_result(action_id, start, safe_err, code, "navigation", recoverable=True)

    async def aobserve(self) -> BrowserObservation:
        """Observe active page and construct structured, sanitized DOM representation."""
        try:
            await self._ensure_active_page()
            assert self._page is not None

            url = self._page.url
            title = await self._page.title()

            # Extract visible text content safely
            try:
                raw_text = await self._page.inner_text("body", timeout=self.action_timeout_ms)
            except Exception:
                raw_text = ""

            sanitized_text = self.security.sanitize_text(raw_text)

            # Discover interactive elements (buttons, inputs, links, selects)
            interactive_elements = await self._extract_interactive_elements()

            # Extract form summaries with credential values redacted
            forms = await self._extract_forms()

            # Extract hyperlinks
            links = await self._extract_links()

            # Extract scroll position
            scroll_pos = await self._get_scroll_position()

            return BrowserObservation(
                url=url,
                title=title,
                text_content=sanitized_text,
                interactive_elements=interactive_elements,
                forms=forms,
                links=links,
                scroll_position=scroll_pos,
                viewport=dict(self.viewport),
                status_code=200,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            logger.warning("Observation extraction degraded: %s", safe_err)
            fallback_title = ""
            if self._page is not None:
                try:
                    if hasattr(self._page, "title"):
                        t_val = self._page.title()
                        fallback_title = await t_val if asyncio.iscoroutine(t_val) else str(t_val)
                except Exception:
                    fallback_title = ""

            return BrowserObservation(
                url=getattr(self._page, "url", ""),
                title=fallback_title,
                text_content="",
                error=BrowserError(
                    code="OBSERVATION_FAILED",
                    message=safe_err,
                    category="dom",
                    recoverable=True,
                ),
            )

    async def aclick(self, selector: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Click an interactive element matching selector."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        timeout = timeout_ms or self.action_timeout_ms

        try:
            await self._ensure_active_page()
            assert self._page is not None

            locator = self._page.locator(selector).first
            await locator.click(timeout=timeout)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"clicked": selector},
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except PlaywrightTimeoutError:
            safe_msg = f"Click timed out on element '{selector}' after {timeout}ms."
            return self._build_failure_result(
                action_id, start, safe_msg, "TIMEOUT", "timeout", recoverable=True, selector=selector
            )
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "ELEMENT_NOT_FOUND" if "not found" in safe_err.lower() or "no element" in safe_err.lower() else "CLICK_FAILED"
            return self._build_failure_result(
                action_id, start, safe_err, code, "dom", recoverable=True, selector=selector
            )

    async def atype_text(
        self,
        selector: str,
        text: str,
        clear_existing: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Enter text into an input or textarea element with secret protection."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        timeout = timeout_ms or self.action_timeout_ms

        try:
            await self._ensure_active_page()
            assert self._page is not None

            locator = self._page.locator(selector).first
            if clear_existing:
                await locator.fill("", timeout=timeout)

            await locator.fill(text, timeout=timeout)

            # Redact sensitive preview in output result
            sanitized_preview = self.security.sanitize_text(text)
            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={
                    "selector": selector,
                    "typed_length": len(text),
                    "preview": sanitized_preview,
                },
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except PlaywrightTimeoutError:
            safe_msg = f"Typing timed out on element '{selector}' after {timeout}ms."
            return self._build_failure_result(
                action_id, start, safe_msg, "TIMEOUT", "timeout", recoverable=True, selector=selector
            )
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "ELEMENT_NOT_FOUND" if "not found" in safe_err.lower() else "TYPE_FAILED"
            return self._build_failure_result(
                action_id, start, safe_err, code, "dom", recoverable=True, selector=selector
            )

    async def aselect_option(
        self,
        selector: str,
        value: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Select an option in a <select> element by value or label."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        timeout = timeout_ms or self.action_timeout_ms

        try:
            await self._ensure_active_page()
            assert self._page is not None

            locator = self._page.locator(selector).first
            # Support selecting by value, label, or index
            selected = await locator.select_option(value=value, timeout=timeout)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"selector": selector, "selected": selected or [value]},
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except PlaywrightTimeoutError:
            safe_msg = f"Option selection timed out on '{selector}' after {timeout}ms."
            return self._build_failure_result(
                action_id, start, safe_msg, "TIMEOUT", "timeout", recoverable=True, selector=selector
            )
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "ELEMENT_NOT_FOUND" if "not found" in safe_err.lower() else "SELECT_FAILED"
            return self._build_failure_result(
                action_id, start, safe_err, code, "dom", recoverable=True, selector=selector
            )

    async def ascroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> ActionResult:
        """Scroll the active page view."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        delta = amount if amount is not None else 500

        try:
            await self._ensure_active_page()
            assert self._page is not None

            if direction == "down":
                await self._page.evaluate(f"window.scrollBy(0, {delta});")
            elif direction == "up":
                await self._page.evaluate(f"window.scrollBy(0, -{delta});")
            elif direction == "top":
                await self._page.evaluate("window.scrollTo(0, 0);")
            elif direction == "bottom":
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            else:
                raise BrowserActionError(f"Invalid scroll direction: '{direction}'", action="scroll")

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"direction": direction, "scroll_position": obs.scroll_position},
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            return self._build_failure_result(action_id, start, safe_err, "SCROLL_FAILED", "action", recoverable=True)

    async def aextract_content(
        self,
        selector: Optional[str] = None,
        extract_type: str = "text",
    ) -> ActionResult:
        """Extract structured content ('text', 'html', 'table') from the page."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            await self._ensure_active_page()
            assert self._page is not None

            target = self._page.locator(selector).first if selector else self._page.locator("body")

            if extract_type == "html":
                content = await target.inner_html(timeout=self.action_timeout_ms)
            elif extract_type == "table":
                # Extract HTML table to list of dictionaries
                rows_data = await target.evaluate("""
                    el => {
                        const table = el.tagName === 'TABLE' ? el : el.querySelector('table');
                        if (!table) return [];
                        const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
                        const rows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => !r.querySelector('th'));
                        return rows.map(row => {
                            const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
                            if (headers.length === cells.length) {
                                return headers.reduce((obj, h, i) => ({ ...obj, [h]: cells[i] }), {});
                            }
                            return cells;
                        });
                    }
                """)
                content = rows_data
            else:  # default "text"
                raw_text = await target.inner_text(timeout=self.action_timeout_ms)
                content = self.security.sanitize_text(raw_text)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"extracted_type": extract_type, "content": content},
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "ELEMENT_NOT_FOUND" if "not found" in safe_err.lower() else "EXTRACTION_FAILED"
            return self._build_failure_result(
                action_id, start, safe_err, code, "dom", recoverable=True, selector=selector
            )

    async def aupload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        """Upload file via input element after strict workspace path verification."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            # 1. Security check: strictly validate path against allowed upload directory
            safe_file = self.security.validate_upload_path(file_path)

            await self._ensure_active_page()
            assert self._page is not None

            # 2. Set file inputs on locator
            locator = self._page.locator(selector).first
            await locator.set_input_files(str(safe_file), timeout=self.action_timeout_ms)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={
                    "selector": selector,
                    "file_name": safe_file.name,
                    "file_path": str(safe_file),
                    "size_bytes": safe_file.stat().st_size,
                },
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except BrowserSecurityError as err:
            return self._build_failure_result(
                action_id, start, err.message, err.code, err.category, recoverable=False, selector=selector
            )
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            code = "ELEMENT_NOT_FOUND" if "not found" in safe_err.lower() else "UPLOAD_FAILED"
            return self._build_failure_result(
                action_id, start, safe_err, code, "io", recoverable=True, selector=selector
            )

    async def adownload_file(
        self,
        trigger_selector: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Trigger and safely save a downloaded file within approved directory boundaries."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        timeout = timeout_ms or self.default_timeout_ms

        try:
            await self._ensure_active_page()
            assert self._page is not None

            # 1. Validate destination path
            safe_dest = self.security.validate_download_path(save_path)

            # 2. Expect download event while triggering download action
            async with self._page.expect_download(timeout=timeout) as download_info:
                if trigger_selector:
                    locator = self._page.locator(trigger_selector).first
                    await locator.click(timeout=self.action_timeout_ms)

            download = await download_info.value

            # Determine final destination file
            suggested_filename = download.suggested_filename
            if safe_dest.is_dir():
                target_file = (safe_dest / suggested_filename).resolve()
            else:
                target_file = safe_dest

            # Verify resolved target file still abides by download directory security
            self.security.validate_download_path(target_file)

            # Save file
            await download.save_as(str(target_file))

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={
                    "download_path": str(target_file),
                    "file_name": target_file.name,
                    "bytes": target_file.stat().st_size if target_file.exists() else 0,
                },
                observation=obs,
                latency_ms=round(latency, 2),
            )

        except BrowserSecurityError as err:
            return self._build_failure_result(
                action_id, start, err.message, err.code, err.category, recoverable=False
            )
        except PlaywrightTimeoutError:
            safe_msg = f"Download timed out after {timeout}ms."
            return self._build_failure_result(action_id, start, safe_msg, "TIMEOUT", "timeout", recoverable=True)
        except Exception as err:
            safe_err = self.security.sanitize_text(str(err))
            return self._build_failure_result(action_id, start, safe_err, "DOWNLOAD_FAILED", "io", recoverable=True)

    async def aclose(self) -> None:
        """Safely close active pages, context, and browser instance without leaking resources."""
        async with self._lock:
            if self._is_closed:
                return
            await self._cleanup_resources()
            self._is_closed = True
            logger.info("Playwright browser session closed cleanly.")

    async def _ensure_active_page(self) -> None:
        """Ensure active browser page exists and is not closed."""
        if self._page is None or self._is_closed:
            await self.ainitialize()
        if self._page is not None and hasattr(self._page, "is_closed") and self._page.is_closed():
            logger.info("Re-opening closed page in active context.")
            if self._context:
                self._page = await self._context.new_page()
            else:
                await self.ainitialize()

    async def _cleanup_resources(self) -> None:
        """Helper to close all resources in reverse order with exception swallowing."""
        if self._page is not None:
            try:
                if hasattr(self._page, "close"):
                    await self._page.close()
            except Exception:
                pass
            self._page = None

        if self._context is not None:
            try:
                if hasattr(self._context, "close"):
                    await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                if hasattr(self._browser, "close"):
                    await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                if hasattr(self._playwright, "stop"):
                    await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def _extract_interactive_elements(self) -> List[InteractiveElement]:
        """Discover interactive DOM elements with sanitized metadata."""
        if not self._page:
            return []

        try:
            elements_data = await self._page.evaluate("""
                () => {
                    const selectorList = 'button, a[href], input, select, textarea, [role="button"], [role="link"]';
                    const nodes = Array.from(document.querySelectorAll(selectorList)).slice(0, 50);
                    return nodes.map((el, i) => {
                        const rect = el.getBoundingClientRect();
                        const isVisible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        return {
                            element_id: `el-${i}`,
                            tag_name: el.tagName.toLowerCase(),
                            selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : (el.className ? `.${el.className.split(' ')[0]}` : el.tagName.toLowerCase())),
                            text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 100),
                            element_type: el.getAttribute('type') || null,
                            is_visible: isVisible,
                            is_enabled: !el.disabled,
                            bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        };
                    });
                }
            """)
            return [InteractiveElement(**e) for e in elements_data]
        except Exception:
            return []

    async def _extract_forms(self) -> List[Dict[str, Any]]:
        """Extract forms with sanitized input names."""
        if not self._page:
            return []
        try:
            return await self._page.evaluate("""
                () => {
                    return Array.from(document.forms).map(form => ({
                        id: form.id || null,
                        action: form.action || null,
                        method: (form.method || 'GET').toUpperCase(),
                        inputs: Array.from(form.elements).map(el => el.name || el.id || el.tagName.toLowerCase())
                    }));
                }
            """)
        except Exception:
            return []

    async def _extract_links(self) -> List[Dict[str, str]]:
        """Extract anchor links from page."""
        if not self._page:
            return []
        try:
            raw_links = await self._page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]')).slice(0, 30).map(a => ({
                        text: (a.innerText || '').trim().slice(0, 80),
                        href: String(a.href || '')
                    }));
                }
            """)
            if isinstance(raw_links, list):
                return [
                    {"text": str(item.get("text", "")), "href": str(item.get("href", ""))}
                    for item in raw_links
                    if isinstance(item, dict)
                ]
            return []
        except Exception:
            return []

    async def _get_scroll_position(self) -> Dict[str, int]:
        """Get window scroll coordinates."""
        if not self._page:
            return {"x": 0, "y": 0}
        try:
            return await self._page.evaluate("() => ({ x: Math.round(window.scrollX), y: Math.round(window.scrollY) })")
        except Exception:
            return {"x": 0, "y": 0}

    def _build_failure_result(
        self,
        action_id: str,
        start_time: float,
        error_message: str,
        error_code: str,
        category: str,
        recoverable: bool,
        selector: Optional[str] = None,
    ) -> ActionResult:
        """Helper to standardize error response payloads."""
        latency = (time.perf_counter() - start_time) * 1000
        safe_msg = self.security.sanitize_text(error_message)

        return ActionResult(
            action_id=action_id,
            success=False,
            error=safe_msg,
            error_code=error_code,
            error_category=category,
            recoverable=recoverable,
            latency_ms=round(latency, 2),
            metadata={"selector": selector} if selector else {},
        )


__all__ = ["PlaywrightBrowserAdapter"]
