from __future__ import annotations

from pathlib import Path

from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.logging import get_logger

log = get_logger("apply.browser")

PORTAL_LOGIN = {
    "linkedin": "https://www.linkedin.com/login",
    "indeed": "https://secure.indeed.com/auth",
    "computrabajo": "https://candidato.ar.computrabajo.com/acceso/",
}


async def capture_login(portal: str, state_path: Path) -> Path:
    """Open the portal login page and save Playwright storage_state after the user logs in."""
    url = PORTAL_LOGIN.get(portal)
    if not url:
        raise ValueError(f"No login URL for portal {portal}")
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("playwright is not installed") from exc

    state_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        print(f"Iniciá sesión en {portal} en el navegador. Cuando termines, volvé acá y presioná Enter.")
        await _wait_enter()
        await context.storage_state(path=str(state_path))
        await browser.close()
    log.info("playwright_state_saved", path=str(state_path))
    return state_path


async def _wait_enter() -> None:
    import asyncio

    await asyncio.to_thread(input)


async def apply_in_browser(
    *,
    vacancy: Vacancy,
    package: ApplicationPackage,
    state_path: Path | None,
    screenshot_dir: Path,
    dry_run: bool,
) -> ApplyOutcome:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return ApplyOutcome(ok=False, detail="playwright is not installed")

    storage = str(state_path) if state_path and state_path.exists() else None
    if storage is None:
        return ApplyOutcome(
            ok=False,
            detail=f"missing Playwright session for {vacancy.portal.value}; run: python -m autoapply login {vacancy.portal.value}",
        )

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot = screenshot_dir / f"{vacancy.portal.value}-{vacancy.external_id}.png"
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=storage)
            page = await context.new_page()
            await page.goto(vacancy.apply_url or vacancy.url, wait_until="domcontentloaded", timeout=45000)
            await _maybe_click_apply(page, vacancy.portal.value)
            await _fill_common_fields(page, package)
            await _upload_cv(page, package.cv_pdf_path)
            await page.screenshot(path=str(screenshot), full_page=True)
            if dry_run:
                await browser.close()
                return ApplyOutcome(
                    ok=True,
                    confirmation_id="browser-dry-run",
                    detail="stopped before submit",
                    screenshot_path=str(screenshot),
                )
            submitted = await _submit(page)
            await page.screenshot(path=str(screenshot), full_page=True)
            await browser.close()
            if not submitted:
                return ApplyOutcome(
                    ok=False,
                    detail="could not find a submit control",
                    screenshot_path=str(screenshot),
                )
            return ApplyOutcome(
                ok=True,
                confirmation_id=f"browser:{vacancy.external_id}",
                detail="submitted via Playwright",
                screenshot_path=str(screenshot),
            )
    except Exception as exc:
        log.warning("browser_apply_failed", error=str(exc), portal=vacancy.portal.value)
        return ApplyOutcome(ok=False, detail=str(exc), screenshot_path=str(screenshot) if screenshot.exists() else None)


async def _maybe_click_apply(page, portal: str) -> None:
    labels = {
        "linkedin": ["Easy Apply", "Solicitud sencilla", "Apply"],
        "indeed": ["Apply now", "Postularme", "Aplicar"],
        "computrabajo": ["Postularme", "Postular", "Aplicar"],
    }.get(portal, ["Apply", "Postularme"])
    for label in labels:
        button = page.get_by_role("button", name=label)
        try:
            if await button.count():
                await button.first.click(timeout=3000)
                return
        except Exception:
            continue
        link = page.get_by_role("link", name=label)
        try:
            if await link.count():
                await link.first.click(timeout=3000)
                return
        except Exception:
            continue


async def _fill_common_fields(page, package: ApplicationPackage) -> None:
    # Best-effort; portals vary. Never invent extra answers.
    pairs = [
        ('input[type="email"]', package.candidate_email),
        ('input[name*="email" i]', package.candidate_email),
        ('input[name*="name" i]', package.candidate_name),
    ]
    for selector, value in pairs:
        if not value:
            continue
        locator = page.locator(selector)
        try:
            if await locator.count():
                await locator.first.fill(value)
        except Exception:
            continue


async def _upload_cv(page, cv_pdf_path: str | None) -> None:
    if not cv_pdf_path:
        return
    locator = page.locator('input[type="file"]')
    try:
        if await locator.count():
            await locator.first.set_input_files(cv_pdf_path)
    except Exception:
        log.info("cv_upload_skipped")


async def _submit(page) -> bool:
    for label in ("Submit", "Enviar", "Send application", "Postularme", "Aplicar"):
        button = page.get_by_role("button", name=label)
        try:
            if await button.count():
                await button.first.click(timeout=4000)
                return True
        except Exception:
            continue
    return False
