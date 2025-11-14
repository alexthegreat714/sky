import argparse
import asyncio
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright


PROFILE_DIR = Path("C:/Users/blyth/AppData/Local/Sky/profiles/garmin").expanduser()
DOWNLOAD_DIR = Path("C:/Users/blyth/Desktop/Engineering/Sky/downloads/garmin").expanduser()
SELECTORS_PATH = Path(__file__).with_name("garmin_selectors.json")


def build_sleep_url(d: date) -> str:
    return f"https://connect.garmin.com/modern/sleep/{d.strftime('%Y-%m-%d')}/0"


async def ensure_dirs() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def open_chrome_persistent(headless: bool):
    await ensure_dirs()
    pw = await async_playwright().start()
    browser = await pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="chrome",
        headless=headless,
        accept_downloads=True,
        args=["--disable-gpu-sandbox", "--no-sandbox"],
    )
    page = await browser.new_page()
    return pw, browser, page


async def interactive_login() -> None:
    pw, browser, page = await open_chrome_persistent(headless=False)
    try:
        await page.goto("https://connect.garmin.com/modern", wait_until="domcontentloaded")
        print("Login window opened in Chrome. Please sign in and complete any MFA. Close the window when done.")
        # Keep the browser open until user closes it
        await browser.wait_for_event("close")
    finally:
        await pw.stop()


def _load_selectors() -> dict:
    # Default fallback selectors if no config file exists
    defaults = {
        "menu_button": [
            "role:button:More options",
            "role:button:Options",
            "role:button:Menu",
            "text:/⋮/",
            "css:button[aria-label*='More']",
            "css:button[aria-label*='Options']",
        ],
        "csv_item": [
            "role:menuitem:Download CSV",
            "role:menuitem:CSV",
            "text:/Export.*CSV/i",
            "text:/CSV/i",
        ],
    }
    if not SELECTORS_PATH.exists():
        SELECTORS_PATH.write_text(
            (
                '{\n'
                '  "menu_button": ["role:button:More options", "text:/⋮/", "css:button[aria-label*=More]"] ,\n'
                '  "csv_item":   ["role:menuitem:Download CSV", "text:/CSV/i"]\n'
                '}\n'
            ),
            encoding="utf-8",
        )
        return defaults
    try:
        import json
        data = json.loads(SELECTORS_PATH.read_text(encoding="utf-8"))
        # Merge with defaults to ensure both keys exist
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return defaults


def _resolve_locator(page, spec: str):
    # Spec formats: role:<role>:<name> | text:<text or /regex/> | css:<selector>
    spec = spec.strip()
    try:
        if spec.lower().startswith("role:"):
            _, role, name = spec.split(":", 2)
            if name.startswith("/") and name.endswith("/"):
                pattern = name.strip("/")
                return page.get_by_role(role, name=re.compile(pattern, re.I))
            else:
                return page.get_by_role(role, name=name)
        if spec.lower().startswith("text:"):
            name = spec.split(":", 1)[1]
            if name.startswith("/") and name.endswith("/i"):
                pattern = name[1:-2]
                return page.get_by_text(re.compile(pattern, re.I))
            if name.startswith("/") and name.endswith("/"):
                pattern = name.strip("/")
                return page.get_by_text(re.compile(pattern))
            return page.get_by_text(name)
        if spec.lower().startswith("css:"):
            css = spec.split(":", 1)[1]
            return page.locator(css)
        # fallback treat as text
        return page.get_by_text(spec)
    except Exception:
        return None


async def try_click_download(page, wait_seconds: float = 15.0) -> Optional[Path]:
    sel = _load_selectors()
    # 1) Click the 3-dots / menu button
    clicked = False
    for spec in sel.get("menu_button", []):
        loc = _resolve_locator(page, spec)
        if not loc:
            continue
        try:
            if await loc.is_visible(timeout=1500):
                await loc.click()
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        return None

    # 2) Click CSV/Export item and capture the download
    try:
        async with page.expect_download(timeout=int(wait_seconds * 1000)) as dl_info:
            selected = False
            for spec in sel.get("csv_item", []):
                ml = _resolve_locator(page, spec)
                if not ml:
                    continue
                try:
                    if await ml.is_visible(timeout=1500):
                        await ml.click()
                        selected = True
                        break
                except Exception:
                    continue
            if not selected:
                # provoke timeout quickly if no selector fits
                await page.wait_for_timeout(500)
        download = await dl_info.value
        suggested = download.suggested_filename or f"garmin_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target = DOWNLOAD_DIR / suggested
        await download.save_as(str(target))
        return target
    except Exception:
        return None


async def detect_login_state(page) -> bool:
    """Return True if we appear to be logged in on the target page.

    Heuristics:
    - If URL contains sso.garmin.com or '/signin', assume not logged in.
    - If password input visible, assume not logged in.
    - If URL path contains '/modern/sleep/', assume logged in.
    """
    try:
        url = page.url or ""
        if "sso.garmin.com" in url or "/signin" in url:
            return False
        # quick check for password inputs
        try:
            pw_inputs = await page.locator("input[type=password]").count()
            if pw_inputs and pw_inputs > 0:
                return False
        except Exception:
            pass
        if "/modern/sleep/" in url:
            return True
    except Exception:
        pass
    return False


async def run_download(target_date: Optional[str], headless: bool = True) -> Optional[Path]:
    if target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        # Default to yesterday (often sleep data finalizes in the morning)
        d = date.today() - timedelta(days=1)

    url = build_sleep_url(d)
    pw, browser, page = await open_chrome_persistent(headless=headless)
    try:
        await page.goto(url, wait_until="domcontentloaded")
        # Give the page some time to load data; adjust if needed
        await page.wait_for_timeout(2000)

        path = await try_click_download(page)
        if path:
            # Rename with date prefix for consistency
            dated = DOWNLOAD_DIR / f"sleep-{d.strftime('%Y-%m-%d')}-{path.name}"
            try:
                path.replace(dated)
                return dated
            except Exception:
                return path
        else:
            # No screenshots per request; just report that selectors didn't match
            print("Download controls not detected. Update selectors in garmin_selectors.json and retry.")
            return None
    finally:
        await browser.close()
        await pw.stop()


def main() -> None:
    ap = argparse.ArgumentParser(description="Garmin Sleep Downloader (persistent Chrome profile)")
    ap.add_argument("--init-login", action="store_true", help="Open Chrome to sign in once and persist session")
    ap.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (default: yesterday)")
    ap.add_argument("--no-headless", action="store_true", help="Run Chrome with UI for troubleshooting")
    ap.add_argument("--check-only", action="store_true", help="Just navigate and report login status (no screenshots)")
    ap.add_argument("--print-candidates", action="store_true", help="List likely menu and CSV elements to help build selectors")
    ap.add_argument("--select-flow", action="store_true", help="Interactive selector capture: pick 3-dots and CSV from a headful list")
    ap.add_argument("--capture-clicks", action="store_true", help="Click-to-capture: you click targets, we record attributes and build selectors")
    args = ap.parse_args()

    if args.init_login:
        asyncio.run(interactive_login())
        return

    async def _check() -> None:
        # Navigate to date page and report status; save screenshot
        d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else (date.today() - timedelta(days=1))
        url = build_sleep_url(d)
        pw, browser, page = await open_chrome_persistent(headless=not args.no_headless)
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            ok = await detect_login_state(page)
            state = "LOGGED_IN" if ok else "LOGIN_REQUIRED"
            print(f"CHECK: {state}\nURL: {page.url}\nTitle: {await page.title()}")
        finally:
            await browser.close()
            await pw.stop()

    if args.check_only:
        asyncio.run(_check())
        return

    async def _select_flow() -> None:
        # Open previous day by default, let user select elements, and persist to JSON
        sel = _load_selectors()
        d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else (date.today() - timedelta(days=1))
        url = build_sleep_url(d)
        pw, browser, page = await open_chrome_persistent(headless=False)
        try:
            print(f"Opening: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)

            # List buttons likely to be the 3-dots / options
            buttons = page.locator("button")
            count = await buttons.count()
            print(f"\nCandidate buttons (pick the 3-dots / options control). Found {count}, showing up to 60:\n")
            btn_map = []
            for i in range(min(count, 60)):
                b = buttons.nth(i)
                try:
                    aria = await b.get_attribute("aria-label")
                except Exception:
                    aria = None
                try:
                    title = await b.get_attribute("title")
                except Exception:
                    title = None
                try:
                    txt = (await b.inner_text()).strip()
                except Exception:
                    txt = ""
                label = aria or title or txt
                if not label:
                    continue
                if len(label) > 80:
                    label_disp = label[:77] + "..."
                else:
                    label_disp = label
                print(f"[{i}] label='{label_disp}' text='{txt[:40]}'")
                btn_map.append((i, label, txt))

            def _prompt_idx(prompt: str, max_idx: int) -> int:
                while True:
                    s = input(prompt).strip()
                    if not s.isdigit():
                        print("Enter a number.")
                        continue
                    n = int(s)
                    if 0 <= n <= max_idx:
                        return n
                    print("Out of range.")

            if not btn_map:
                print("No labeled buttons found. Try --print-candidates and adjust selectors manually.")
                return
            choice = _prompt_idx("Enter index for the 3-dots/options button: ", min(count - 1, 59))
            try:
                await buttons.nth(choice).click()
            except Exception as e:
                print(f"Click failed: {e}. You can still save the label.")

            # After opening the menu, gather menuitems
            await page.wait_for_timeout(600)
            items = page.get_by_role("menuitem")
            try:
                mcount = await items.count()
            except Exception:
                mcount = 0
            print(f"\nMenu items (pick the CSV/Export entry). Found {mcount}, showing up to 40:\n")
            csv_map = []
            for i in range(min(mcount, 40)):
                it = items.nth(i)
                try:
                    itxt = (await it.inner_text()).strip()
                except Exception:
                    itxt = ""
                print(f"[{i}] text='{itxt}'")
                csv_map.append((i, itxt))

            if not csv_map:
                print("No menu items detected. Manually open the menu and rerun, or use --print-candidates.")
                return
            csv_choice = _prompt_idx("Enter index for the CSV menu item: ", min(mcount - 1, 39))

            # Build selectors from chosen labels
            chosen_btn_label = None
            for idx, label, txt in btn_map:
                if idx == choice:
                    chosen_btn_label = label
                    break
            chosen_csv_text = None
            for idx, itxt in csv_map:
                if idx == csv_choice:
                    chosen_csv_text = itxt
                    break

            if chosen_btn_label:
                entry = f"role:button:{chosen_btn_label}"
                btn_list = sel.get("menu_button", [])
                # put first
                btn_list = [entry] + [x for x in btn_list if x != entry]
                sel["menu_button"] = btn_list
            if chosen_csv_text:
                entry2 = f"role:menuitem:{chosen_csv_text}"
                csv_list = sel.get("csv_item", [])
                csv_list = [entry2] + [x for x in csv_list if x != entry2]
                sel["csv_item"] = csv_list

            # Persist
            import json
            SELECTORS_PATH.write_text(json.dumps(sel, indent=2), encoding="utf-8")
            print(f"\nSaved selectors to: {SELECTORS_PATH}")
        finally:
            await browser.close()
            await pw.stop()

    if args.select_flow:
        asyncio.run(_select_flow())
        return

    async def _install_capture(page):
        await page.evaluate(
            """
            (function(){
              window.__cap = null;
              function infoFor(el){
                if(!el) return null;
                const getText = (n)=> (n.innerText||'').trim().replace(/\s+/g,' ').slice(0,200);
                const attrs = {};
                const keys = ['id','role','aria-label','title','data-testid','data-test','data-test-id','data-qa','class'];
                for (const k of keys){ try { attrs[k] = el.getAttribute(k); } catch(e){ attrs[k] = null; } }
                function cssPath(node){
                  const parts=[];
                  let depth=0;
                  while(node && node.nodeType===1 && depth<6){
                    let seg=node.nodeName.toLowerCase();
                    if(node.id){ seg += '#' + node.id; parts.unshift(seg); break; }
                    const cls=(node.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean)[0];
                    if(cls){ seg += '.'+cls.replace(/[^a-zA-Z0-9_-]/g,''); }
                    let i=1, sib=node;
                    while((sib=sib.previousElementSibling)) if(sib.nodeName===node.nodeName) i++;
                    seg += ':nth-of-type(' + i + ')';
                    parts.unshift(seg);
                    node=node.parentElement; depth++;
                  }
                  return parts.join(' > ');
                }
                return { tag: el.nodeName, text: getText(el), attrs, cssPath: cssPath(el), outer: (el.outerHTML||'').slice(0,200) };
              }
              function handler(e){ window.__cap = infoFor(e.target); e.preventDefault(); e.stopPropagation(); }
              document.addEventListener('click', handler, {capture:true, once:true});
            })();
            """
        )

    def _build_selectors_from_cap(cap: dict, for_menu_button: bool) -> list[str]:
        sels: list[str] = []
        attrs = cap.get('attrs') or {}
        role = (attrs.get('role') or '').strip()
        aria = (attrs.get('aria-label') or '').strip()
        title = (attrs.get('title') or '').strip()
        did = (attrs.get('id') or '').strip()
        dtest = (attrs.get('data-testid') or attrs.get('data-test') or attrs.get('data-test-id') or attrs.get('data-qa') or '').strip()
        text = (cap.get('text') or '').strip()
        # Prefer role+aria/title, then text, then stable CSS by id/data-test
        name = aria or title
        if role and name:
            sels.append(f"role:{role}:{name}")
        if text and len(text) <= 80:
            safe = text.replace('"', '\\"')
            sels.append(f'text:/^{safe}$/i')
            sels.append(f'text:/{safe}/i')
        if did:
            sels.append(f'css:#{did}')
        if dtest:
            dval = dtest.replace('"','\\"')
            sels.append(f'css:[data-testid="{dval}"]')
        cssp = (cap.get('cssPath') or '').strip()
        if cssp:
            sels.append(f'css:{cssp}')
        if for_menu_button:
            sels += ['role:button:More options','css:button[aria-label*="More"]','text:/⋮/']
        else:
            sels += ['role:menuitem:Download CSV','text:/CSV/i']
        seen=set(); out=[]
        for s in sels:
            if s and s not in seen:
                out.append(s); seen.add(s)
        return out

    async def _capture_clicks() -> None:
        sel = _load_selectors()
        d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else (date.today() - timedelta(days=1))
        url = build_sleep_url(d)
        pw, browser, page = await open_chrome_persistent(headless=False)
        try:
            print(f"Opening: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(800)
            print("\nStep 1: Click the 3-dots/options button in the Chrome window, then wait...")
            await _install_capture(page)
            await page.wait_for_function("window.__cap !== null", timeout=60000)
            cap1 = await page.evaluate("window.__cap")
            print("\nCaptured MENU BUTTON attributes:")
            print(cap1)
            btn_sels = _build_selectors_from_cap(cap1, True)
            print("\nBuilt selectors (menu_button):")
            for s in btn_sels[:8]:
                print("  ", s)
            loc = _resolve_locator(page, btn_sels[0])
            try:
                if loc:
                    await loc.click(timeout=2000)
                    await page.wait_for_timeout(600)
            except Exception:
                pass
            print("\nStep 2: Click the CSV/Export item in the menu, then wait...")
            await _install_capture(page)
            await page.wait_for_function("window.__cap !== null", timeout=60000)
            cap2 = await page.evaluate("window.__cap")
            print("\nCaptured CSV ITEM attributes:")
            print(cap2)
            csv_sels = _build_selectors_from_cap(cap2, False)
            print("\nBuilt selectors (csv_item):")
            for s in csv_sels[:8]:
                print("  ", s)
            sel["menu_button"] = btn_sels + [x for x in sel.get("menu_button", []) if x not in btn_sels]
            sel["csv_item"] = csv_sels + [x for x in sel.get("csv_item", []) if x not in csv_sels]
            import json
            SELECTORS_PATH.write_text(json.dumps(sel, indent=2), encoding="utf-8")
            print(f"\nSaved selectors to: {SELECTORS_PATH}")
        finally:
            await browser.close()
            await pw.stop()

    if args.capture_clicks:
        asyncio.run(_capture_clicks())
        return

    async def _print_candidates() -> None:
        d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else (date.today() - timedelta(days=1))
        url = build_sleep_url(d)
        pw, browser, page = await open_chrome_persistent(headless=not args.no_headless)
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            # Find candidate buttons (potential kebab/3-dots) and menu items
            buttons = page.locator("button")
            count = await buttons.count()
            print(f"Found {count} buttons. Listing up to 40 candidates:\n")
            limit = min(count, 40)
            for i in range(limit):
                b = buttons.nth(i)
                try:
                    txt = (await b.inner_text()).strip()
                except Exception:
                    txt = ""
                try:
                    aria = await b.get_attribute("aria-label")
                except Exception:
                    aria = None
                try:
                    title = await b.get_attribute("title")
                except Exception:
                    title = None
                label = aria or title or txt
                if label and ("download" in label.lower() or "export" in label.lower() or "more" in label.lower() or "options" in label.lower() or "⋮" in label):
                    print(f"button[{i}] label='{label}' text='{txt[:40]}'")

            # Menuitems (if any menu is already open)
            items = page.get_by_role("menuitem")
            try:
                mcount = await items.count()
            except Exception:
                mcount = 0
            if mcount:
                print(f"\nFound {mcount} menuitems:")
                for i in range(min(mcount, 20)):
                    it = items.nth(i)
                    try:
                        itxt = (await it.inner_text()).strip()
                    except Exception:
                        itxt = ""
                    print(f"menuitem[{i}] text='{itxt}'")
            print("\nEdit garmin_selectors.json to add precise selectors if needed.")
        finally:
            await browser.close()
            await pw.stop()

    if args.print_candidates:
        asyncio.run(_print_candidates())
        return

    path = asyncio.run(run_download(args.date, headless=not args.no_headless))
    if path:
        print(f"Saved: {path}")
    else:
        print("No download captured. Use --no-headless and share the screenshot to refine selectors.")


if __name__ == "__main__":
    main()
