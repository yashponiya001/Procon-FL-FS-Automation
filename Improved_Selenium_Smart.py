
import os
import csv
import time
import logging
import datetime

from dataclasses import dataclass
from typing import Dict, Any, Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

try:
    import anthropic as _anthropic_lib
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


# =========================================================
# CONFIG
# =========================================================

@dataclass
class FrameworkConfig:

    execution_file: str = "ExecutionSequence.csv"

    # Path to the folder that holds the module CSV files.
    # Override via env var or pass directly:
    #   FrameworkConfig(module_base_path="/your/path")
    module_base_path: str = os.environ.get(
        "LOCATORS_BASE_PATH",
        os.path.join(os.path.dirname(__file__), "LocatorsFiles")
    )

    timeout: int = 30           # seconds to wait for each element

    # Path to the folder that holds standalone Python scripts
    # called via the RUN_SCRIPT action.
    # Override via env var or pass directly:
    #   FrameworkConfig(scripts_path="/your/scripts")
    scripts_path: str = os.environ.get(
        "SCRIPTS_PATH",
        os.path.join(os.path.dirname(__file__), "Scripts")
    )

    # Pause between every step in seconds.
    # Gives the browser time to render after each action.
    # Increase if the app is slow to respond.
    step_delay: float = 3.0

    # Wait for page to fully load (document.readyState == complete)
    # before executing each step. Helps with slow page navigations.
    wait_for_page_load: bool = True

    # Smart locator resolution
    # True  → framework finds elements by text/ARIA automatically.
    # False → CSV must supply Locator + Locator Value columns as before.
    smart_locator: bool = True

    # True  → falls back to Claude Vision when text/ARIA discovery fails.
    # Requires ANTHROPIC_API_KEY environment variable.
    ai_locator_fallback: bool = False

    headless: bool = False

    # True  → mark step FAIL and continue to next step/module.
    # False → raise immediately, aborting the current module.
    continue_on_failure: bool = True


# =========================================================
# CREATE FOLDERS
# =========================================================

os.makedirs("logs",        exist_ok=True)
os.makedirs("screenshots", exist_ok=True)


# =========================================================
# LOGGER
# =========================================================

# Timestamp used for both log file names — new files every run
_LOG_TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# File handler – only WARNING and above (keeps framework log lean)
_file_handler = logging.FileHandler(f"logs/framework_{_LOG_TS}.log")
_file_handler.setLevel(logging.WARNING)

# Console handler – DEBUG output so smart locator failures show detail
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[_file_handler, _console_handler]
)

# ------------------------------------------------------------------
# STEP RESULTS LOGGER
# Writes one line per test step to logs/step_results_<timestamp>.log:
#   <timestamp> | <module> | <description> | PASS / FAIL / SKIPPED
# ------------------------------------------------------------------
_step_file_handler = logging.FileHandler(f"logs/step_results_{_LOG_TS}.log")
_step_file_handler.setLevel(logging.INFO)
_step_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(message)s")
)

step_logger = logging.getLogger("StepResults")
step_logger.setLevel(logging.INFO)
step_logger.addHandler(_step_file_handler)
step_logger.propagate = False   # keep step lines out of framework.log

logger = logging.getLogger("EnterpriseFramework")


# =========================================================
# FRAMEWORK CONTEXT
# =========================================================

class FrameworkContext:

    def __init__(self):

        self.exception_count = 0

        # Populated by GET_TEXT; accessible by subsequent steps.
        self.shared_store: Dict[str, Any] = {}

        self.last_captured_text = ""

        # Toggled by START_RECORDING / STOP_RECORDING.
        self.recording_active = False


# =========================================================
# DRIVER FACTORY
# =========================================================

class DriverFactory:

    @staticmethod
    def create_driver(config: "FrameworkConfig"):

        options = Options()

        if config.headless:
            options.add_argument("--headless=new")

        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-popup-blocking")

        # Remove "Chrome is being controlled by automated software" bar
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"]
        )
        options.add_experimental_option(
            "useAutomationExtension", False
        )

        # Suppress "Change your password" / breach detection popup
        # and all other Chrome password manager dialogs.
        options.add_argument(
            "--disable-features=PasswordLeakDetection"
        )
        options.add_experimental_option("prefs", {
            "credentials_enable_service":              False,
            "profile.password_manager_enabled":        False,
            "profile.password_manager_leak_detection": False,
        })

        driver_path = ChromeDriverManager().install()

        # webdriver-manager sometimes returns the NOTICES file path.
        if "THIRD_PARTY_NOTICES" in driver_path:
            binary = (
                "chromedriver.exe"
                if os.name == "nt"
                else "chromedriver"
            )
            driver_path = os.path.join(
                os.path.dirname(driver_path), binary
            )

        logger.info(f"Using ChromeDriver: {driver_path}")

        driver = webdriver.Chrome(
            service=Service(driver_path),
            options=options
        )

        driver.maximize_window()

        return driver


# =========================================================
# WAIT HELPER
# =========================================================

class WaitHelper:

    def __init__(self, driver, timeout: int):

        self.driver = driver
        self.wait   = WebDriverWait(driver, timeout)

    def visible(self, locator):
        return self.wait.until(
            EC.visibility_of_element_located(locator)
        )

    def clickable(self, locator):
        return self.wait.until(
            EC.element_to_be_clickable(locator)
        )

    def present(self, locator):
        return self.wait.until(
            EC.presence_of_element_located(locator)
        )


# =========================================================
# SCREENSHOT UTILITY
# =========================================================

class ScreenshotUtil:

    @staticmethod
    def capture(driver, name: str = "screenshot") -> str:

        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"screenshots/{name}_{ts}.png"

        driver.save_screenshot(path)

        logger.info(f"Screenshot saved: {path}")

        return path


# =========================================================
# CSV UTILITIES
# =========================================================

class CsvUtil:

    @staticmethod
    def _normalize_row(row: dict) -> dict:
        """Lowercase + strip all keys; strip string values.
        Handles None values from short CSV rows, leading apostrophes
        from Excel date formatting, and Excel double-quote escaping.
        """
        def clean_val(v):
            # None means the CSV row had fewer columns than the header
            # Convert to empty string so .strip() never fails
            if v is None:
                return ""
            if isinstance(v, str):
                # Strip leading apostrophe Excel adds to prevent
                # auto-formatting e.g. '05/06/2026 → 05/06/2026
                v = v.strip().lstrip("'")
                # Fix Excel double-quote escaping in CSV
                # Excel saves "root" as ""root"" inside CSV cells
                v = v.replace('""', '"')
                return v
            return v

        def clean_key(k):
            # Guard against None keys from malformed CSV headers
            if k is None:
                return ""
            return str(k).strip().lower()

        return {
            clean_key(k): clean_val(v)
            for k, v in row.items()
        }

    @staticmethod
    def _normalize_key(key: str) -> str:
        return key.strip().lower()

    @staticmethod
    def read_csv(file_path: str) -> tuple:
        """
        Returns (rows, original_fieldnames).

        rows                – list of dicts with normalised
                              (lowercase-stripped) keys, safe for
                              lookup via the CSV_* constants.
        original_fieldnames – the raw header strings exactly as they
                              appear in the file, used by write_csv
                              to restore exact column names + order.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"CSV not found: {file_path}"
            )

        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            original_fieldnames = list(reader.fieldnames or [])
            raw_rows = list(reader)

        rows = [CsvUtil._normalize_row(r) for r in raw_rows]

        return rows, original_fieldnames

    @staticmethod
    def write_csv(
        file_path:           str,
        rows:                list,
        original_fieldnames: list
    ):
        """
        Write rows back to CSV preserving the original header
        casing and column order captured by read_csv.

        Internally rows use normalised (lowercase) keys, so this
        method builds a reverse mapping
        (normalised key → original header) before writing, ensuring
        DictWriter matches every column correctly and no cell goes blank.
        """
        if not rows:
            return

        # Build: normalised_key → original_header
        # e.g. "actions file" → "Actions FIle"
        key_map = {
            CsvUtil._normalize_key(h): h
            for h in original_fieldnames
        }

        # Reconstruct each row with original-cased keys.
        restored_rows = [
            {key_map.get(k, k): v for k, v in row.items()}
            for row in rows
        ]

        with open(
            file_path, mode="w", newline="", encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=original_fieldnames,
                extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(restored_rows)


# =========================================================
# CSV COLUMN CONSTANTS
# (normalised – lowercase, stripped)
# =========================================================

# --- ExecutionSequence.csv ---
ES_MODULE_NAME  = "actions file"            # module CSV name (no ext)
ES_TEST_URL     = "test url"                # URL opened before module
ES_LAST_EXEC    = "last executed date & time"
ES_FAILED_COUNT = "failed"
ES_STATUS       = "status"
ES_RUN          = "run"

# Original header spellings for write-back
ES_FIELDNAMES = [
    "Actions FIle",
    "Test URL",
    "Last Executed Date & Time",
    "Failed",
    "Status",
    "RUN",
]

# --- Module CSVs (e.g. CommunicationCenter.csv) ---
MOD_DESCRIPTION  = "basic sanity"
MOD_ELEMENT      = "element"
MOD_LOCATOR_TYPE = "locator"
MOD_LOCATOR_VAL  = "locator value"
MOD_ACTION       = "action"
MOD_TEST_DATA    = "test data"
MOD_RUN          = "run"
MOD_EXTRA        = "extra data"
MOD_EXECUTED_ON  = "executed on"

# Original header spellings for write-back
MOD_FIELDNAMES = [
    "Basic Sanity",
    "Element",
    "Locator",
    "Locator Value",
    "Action",
    "Test Data",
    "Run",
    "Extra Data",
    "Executed On",
]


# =========================================================
# WEB ACTIONS
# =========================================================

class WebActions:

    def __init__(
        self,
        driver,
        context: FrameworkContext,
        config:  FrameworkConfig
    ):
        self.driver  = driver
        self.context = context
        self.config  = config
        self.wait    = WaitHelper(driver, config.timeout)

    # ----------------------------------------------------------
    # Safe wrapper
    # ----------------------------------------------------------

    def safe_execute(self, action: Callable, name: str):

        try:
            return action()

        except Exception as e:

            self.context.exception_count += 1

            shot = ScreenshotUtil.capture(self.driver, name)

            logger.error(
                f"FAILED: {name} | {e} | Screenshot: {shot}"
            )

            raise

    # ----------------------------------------------------------
    # Navigation
    # ----------------------------------------------------------

    def open_url(self, url: str):
        return self.safe_execute(
            lambda: self.driver.get(url), "open_url"
        )

    def _wait_for_page_load(self):
        """Wait until document.readyState is complete."""
        try:
            WebDriverWait(self.driver, self.config.timeout).until(
                lambda d: d.execute_script(
                    "return document.readyState"
                ) == "complete"
            )
        except Exception:
            pass  # Don't fail the step if this times out

    def _wait_for_overlay(self):
        """
        Wait for any modal overlay, loading spinner, or backdrop to
        disappear before proceeding. Prevents "element click intercepted"
        errors caused by overlays blocking clicks.

        Watches for common overlay patterns:
          - StyledOverlay (this app)
          - loading / spinner classes
          - modal-backdrop
          - Any element with opacity transition
        """
        overlay_xpaths = [
            # This app's specific overlay
            "//*[contains(@class,'StyledOverlay') or "
            "contains(@class,'StyledLayer')]",
            # Generic loading/spinner overlays
            "//*[contains(@class,'loading-overlay') or "
            "contains(@class,'page-loader') or "
            "contains(@class,'spinner-overlay')]",
            # Bootstrap/modal backdrop
            "//*[contains(@class,'modal-backdrop')]",
            # Any element with overlay-style positioning
            "//*[contains(@class,'overlay') and "
            "not(contains(@class,'hidden'))]",
        ]

        for xpath in overlay_xpaths:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.XPATH, xpath))
                )
            except Exception:
                pass  # Overlay not found or already gone — continue

        # Small buffer after overlay clears
        time.sleep(0.5)

    def wait_for_url(self, partial_url: str = ""):
        """
        Wait until the browser URL changes.

        partial_url (Test Data): optional — wait until the URL
        contains this text e.g. "dashboard" or "home".
        If blank, waits until the URL changes from the current one.

        Use after clicking Sign In / Submit to ensure the page has
        fully navigated before the next step runs.
        """
        def action():
            current_url = self.driver.current_url

            if partial_url:
                # Wait until URL contains the expected fragment
                WebDriverWait(self.driver, self.config.timeout).until(
                    lambda d: partial_url.lower() in d.current_url.lower(),
                )
                logger.info(
                    f"  [wait_for_url] URL now contains '{partial_url}': "
                    f"{self.driver.current_url}"
                )
            else:
                # Wait until URL changes from whatever it was
                WebDriverWait(self.driver, self.config.timeout).until(
                    lambda d: d.current_url != current_url
                )
                logger.info(
                    f"  [wait_for_url] URL changed to: {self.driver.current_url}"
                )

        return self.safe_execute(action, "wait_for_url")

    def wait_for_element(self, locator):
        """
        Wait until an element is visible on the page.
        Use after navigation to confirm the target page has loaded.
        """
        return self.safe_execute(
            lambda: self.wait.visible(locator),
            "wait_for_element"
        )

    # ----------------------------------------------------------
    # Element interactions
    # ----------------------------------------------------------

    def click(self, locator):
        def action():
            el = self.wait.clickable(locator)
            try:
                el.click()
            except Exception as e:
                if "intercepted" in str(e).lower() or "not clickable" in str(e).lower():
                    # Overlay is blocking — wait for it then try JS click
                    logger.warning(
                        "  [click] element intercepted by overlay — "
                        "waiting and retrying with JS click"
                    )
                    self._wait_for_overlay()
                    time.sleep(0.5)
                    try:
                        el.click()
                    except Exception:
                        # Final fallback — JavaScript click bypasses overlay
                        self.driver.execute_script(
                            "arguments[0].click();", el
                        )
                else:
                    raise
        return self.safe_execute(action, "click")

    def double_click(self, locator):
        def action():
            el = self.wait.clickable(locator)
            ActionChains(self.driver).double_click(el).perform()
        return self.safe_execute(action, "double_click")

    def enter_text(self, locator, text: str):
        def action():
            el = self.wait.visible(locator)
            el.clear()
            el.send_keys(text)
        return self.safe_execute(action, "enter_text")

    def enter_text_enter(self, locator, text: str):
        def action():
            el = self.wait.visible(locator)
            el.clear()
            el.send_keys(text)
            el.send_keys(Keys.ENTER)
        return self.safe_execute(action, "enter_text_enter")

    def enter_text_with_timestamp(self, locator, text: str):
        """Appends _YYYYMMDD_HHMMSS to the text before typing."""
        def action():
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            el = self.wait.visible(locator)
            el.clear()
            el.send_keys(f"{text}_{ts}")
        return self.safe_execute(
            action, "enter_text_with_timestamp"
        )

    def clear_text(self, locator):
        return self.safe_execute(
            lambda: self.wait.visible(locator).clear(), "clear_text"
        )

    def press_enter(self, locator):
        return self.safe_execute(
            lambda: self.wait.visible(locator).send_keys(
                Keys.ENTER
            ),
            "press_enter"
        )

    def get_text(self, locator):
        def action():
            text = self.wait.visible(locator).text
            self.context.last_captured_text = text
            self.context.shared_store["last_text"] = text
            logger.info(f"Captured text: {text}")
            return text
        return self.safe_execute(action, "get_text")

    # ----------------------------------------------------------
    # Scroll / Screenshot / Sleep
    # ----------------------------------------------------------

    def scroll_down(self):
        return self.safe_execute(
            lambda: self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            ),
            "scroll_down"
        )

    def screenshot(self, name: str = "screenshot"):
        return self.safe_execute(
            lambda: ScreenshotUtil.capture(self.driver, name),
            "screenshot"
        )

    def sleep(self, seconds):
        return self.safe_execute(
            lambda: time.sleep(float(seconds)), "sleep"
        )

    def pause(self, message: str = ""):
        """
        Pause execution and wait for the user to press Enter.
        Useful for debugging — lets you inspect the browser mid-run.
        Test Data = optional message e.g. "Check the form before submitting"
        """
        def action():
            msg = message.strip() if message else "Execution paused"
            print(f"\n{'='*55}")
            print(f"  PAUSED: {msg}")
            print(f"  Browser is open — inspect as needed.")
            print(f"  Press Enter to continue...")
            print(f"{'='*55}")
            input()
            print("  Resuming execution...\n")
        return self.safe_execute(action, "pause")

    # ----------------------------------------------------------
    # Date picker
    # ----------------------------------------------------------

    def select_date(self, locator, date_str: str):
        """
        Select a date in a custom calendar widget.

        date_str format: DD/MM/YYYY  e.g. "04/06/2026"

        Steps:
          1. Click the calendar trigger element (locator).
          2. Set the month via its dropdown/select or prev/next arrows.
          3. Set the year via its dropdown/select or prev/next arrows.
          4. Click the day button that matches the day number.

        The method tries <select> dropdowns first (fastest), then
        falls back to clicking prev/next navigation arrows so it
        works with both native-select and button-nav widgets.
        """
        def action():
            # ── Parse the target date ─────────────────────────
            # Strip leading apostrophe — Excel adds ' prefix to dates
            # to prevent auto-formatting e.g. '05/06/2026 → 05/06/2026
            clean_date = date_str.strip().lstrip("'\"")
            try:
                target = datetime.datetime.strptime(clean_date, "%d/%m/%Y")
            except ValueError:
                raise ValueError(
                    f"SELECT_DATE: invalid date format '{clean_date}'. "
                    "Expected DD/MM/YYYY e.g. 04/06/2026"
                )

            target_day   = target.day
            target_month = target.month      # 1-12
            target_year  = target.year
            month_name   = target.strftime("%B")   # e.g. "June"
            month_abbr   = target.strftime("%b")   # e.g. "Jun"

            # ── Step 1: open the calendar ─────────────────────
            self.wait.clickable(locator).click()
            time.sleep(0.4)

            # ── Step 2: set the YEAR ──────────────────────────
            # Try <select> dropdown first
            year_set = False
            try:
                from selenium.webdriver.support.ui import Select
                year_selects = self.driver.find_elements(
                    By.XPATH,
                    "//select[contains(@class,'year') or "
                    "contains(@aria-label,'year') or "
                    "contains(@aria-label,'Year')]"
                )
                if year_selects:
                    Select(year_selects[0]).select_by_visible_text(str(target_year))
                    year_set = True
                    logger.info(f"  [select_date] year set via <select>: {target_year}")
            except Exception:
                pass

            # Fallback: click the year display and navigate with arrows
            if not year_set:
                try:
                    year_el = self.driver.find_element(
                        By.XPATH,
                        "//*[contains(@class,'year') or "
                        "contains(@aria-label,'year')]"
                        "[not(self::select)]"
                    )
                    current_year = int(year_el.text.strip())
                    diff = target_year - current_year
                    arrow_cls = "next" if diff > 0 else "prev"
                    arrow = self.driver.find_element(
                        By.XPATH,
                        f"//*[contains(@class,'{arrow_cls}') or "
                        f"contains(@aria-label,'{arrow_cls}')]"
                    )
                    for _ in range(abs(diff)):
                        arrow.click()
                        time.sleep(0.15)
                    logger.info(f"  [select_date] year set via arrows: {target_year}")
                except Exception as e:
                    logger.warning(f"  [select_date] could not set year: {e}")

            # ── Step 3: set the MONTH ─────────────────────────
            month_set = False
            try:
                from selenium.webdriver.support.ui import Select
                month_selects = self.driver.find_elements(
                    By.XPATH,
                    "//select[contains(@class,'month') or "
                    "contains(@aria-label,'month') or "
                    "contains(@aria-label,'Month')]"
                )
                if month_selects:
                    # Try full name first, then abbreviation, then number
                    sel = Select(month_selects[0])
                    for label in (month_name, month_abbr, str(target_month)):
                        try:
                            sel.select_by_visible_text(label)
                            month_set = True
                            break
                        except Exception:
                            continue
                    if month_set:
                        logger.info(f"  [select_date] month set via <select>: {month_name}")
            except Exception:
                pass

            # Fallback: navigate month with prev/next arrows
            if not month_set:
                try:
                    month_el = self.driver.find_element(
                        By.XPATH,
                        "//*[contains(@class,'month') or "
                        "contains(@aria-label,'month')]"
                        "[not(self::select)]"
                    )
                    current_text = month_el.text.strip()
                    # Parse current month
                    for fmt in ("%B", "%b"):
                        try:
                            current_month = datetime.datetime.strptime(
                                current_text, fmt
                            ).month
                            break
                        except ValueError:
                            current_month = None

                    if current_month:
                        diff = target_month - current_month
                        arrow_cls = "next" if diff > 0 else "prev"
                        arrow = self.driver.find_element(
                            By.XPATH,
                            f"//*[contains(@class,'{arrow_cls}') or "
                            f"contains(@aria-label,'{arrow_cls}')]"
                        )
                        for _ in range(abs(diff)):
                            arrow.click()
                            time.sleep(0.15)
                        logger.info(
                            f"  [select_date] month set via arrows: {month_name}"
                        )
                except Exception as e:
                    logger.warning(f"  [select_date] could not set month: {e}")

            time.sleep(0.5)

            # ── Step 4: navigate to correct month/year via arrows ──
            # This calendar uses ← → arrow buttons to change month.
            # Read the currently displayed month+year and navigate
            # forward or back until we reach the target month+year.
            max_nav = 24   # safety cap — max 24 arrow clicks
            for _ in range(max_nav):
                # Read current month and year from the dropdowns/selects
                try:
                    from selenium.webdriver.support.ui import Select
                    month_els = self.driver.find_elements(
                        By.XPATH,
                        "//select[contains(@class,'month') or "
                        "contains(@aria-label,'month') or "
                        "contains(@aria-label,'Month')] | "
                        "//*[contains(@class,'StyledCalendar') and self::select]"
                    )
                    year_els = self.driver.find_elements(
                        By.XPATH,
                        "//select[contains(@class,'year') or "
                        "contains(@aria-label,'year') or "
                        "contains(@aria-label,'Year')]"
                    )

                    cur_month = cur_year = None

                    if month_els:
                        sel_m = Select(month_els[0])
                        cur_month_text = sel_m.first_selected_option.text.strip()
                        for fmt in ("%B", "%b"):
                            try:
                                cur_month = datetime.datetime.strptime(
                                    cur_month_text, fmt
                                ).month
                                break
                            except ValueError:
                                pass

                    if year_els:
                        cur_year = int(Select(year_els[0]).first_selected_option.text.strip())

                    if cur_month and cur_year:
                        cur_total  = cur_year  * 12 + cur_month
                        tgt_total  = target_year * 12 + target_month
                        if cur_total == tgt_total:
                            break   # already on correct month+year
                        # Click next (→) or prev (←) arrow
                        if cur_total < tgt_total:
                            arrow = self.driver.find_element(
                                By.XPATH,
                                "//*[contains(@class,'StyledCalendar') and self::button]"
                                "[last()] | "
                                "//button[@aria-label='Next month'] | "
                                "//button[contains(@class,'next')] | "
                                "//*[contains(@class,'StyledCalendar')]//button[last()]"
                            )
                        else:
                            arrow = self.driver.find_element(
                                By.XPATH,
                                "//*[contains(@class,'StyledCalendar') and self::button]"
                                "[1] | "
                                "//button[@aria-label='Previous month'] | "
                                "//button[contains(@class,'prev')] | "
                                "//*[contains(@class,'StyledCalendar')]//button[1]"
                            )
                        arrow.click()
                        time.sleep(0.3)
                        continue

                except Exception as e:
                    logger.warning(f"  [select_date] navigation error: {e}")
                    break

            # ── Step 5: click the day button ──────────────────
            # The calendar renders day buttons with aria-label like
            # "Fri Jun 05 2026" — use this for an exact match.
            # Build all possible aria-label formats Selenium may see.
            day_padded   = str(target_day).zfill(2)   # "05"
            day_unpadded = str(target_day)             # "5"
            month_abbr_up = month_abbr.upper()         # "JUN"

            # Try aria-label first (most reliable for this widget)
            aria_formats = [
                # e.g. "Fri Jun 05 2026"
                target.strftime(f"%a {month_abbr} {day_padded} {target_year}"),
                target.strftime(f"%a {month_abbr} {day_unpadded} {target_year}"),
                # e.g. "Fri Jun 5 2026"
                f"{target.strftime('%a')} {month_abbr} {day_unpadded} {target_year}",
                f"{target.strftime('%a')} {month_abbr} {day_padded} {target_year}",
                # e.g. "June 5, 2026"
                f"{month_name} {day_unpadded}, {target_year}",
                f"{month_name} {day_padded}, {target_year}",
            ]

            day_el = None
            for aria in aria_formats:
                try:
                    els = self.driver.find_elements(
                        By.XPATH,
                        f"//button[@aria-label='{aria}']"
                    )
                    if els:
                        day_el = els[0]
                        logger.info(
                            f"  [select_date] found day via aria-label='{aria}'"
                        )
                        break
                except Exception:
                    continue

            # Fallback: match by day number inside StyledCalendar button
            if not day_el:
                fallback_xpaths = [
                    f"//*[contains(@class,'StyledCalendar')]"
                    f"//button[normalize-space(.)='{day_unpadded}' "
                    f"and not(contains(@class,'disabled'))]",
                    f"//button[normalize-space(.)='{day_unpadded}' "
                    f"and not(contains(@class,'disabled')) "
                    f"and not(contains(@class,'outside'))]",
                    f"//td[normalize-space(text())='{day_unpadded}']",
                    f"//*[@role='gridcell' and normalize-space(.)='{day_unpadded}']",
                ]
                for xpath in fallback_xpaths:
                    try:
                        els = self.driver.find_elements(By.XPATH, xpath)
                        if els:
                            day_el = els[0]
                            logger.info(
                                f"  [select_date] found day via fallback xpath"
                            )
                            break
                    except Exception:
                        continue

            if not day_el:
                raise RuntimeError(
                    f"select_date: could not find day button for "
                    f"{date_str}. Check the date is within the "
                    f"calendar's selectable range."
                )

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'nearest'});", day_el
            )
            time.sleep(0.1)
            day_el.click()
            logger.info(f"  [select_date] clicked day {target_day} ({date_str})")

        return self.safe_execute(action, "select_date")

    # ----------------------------------------------------------
    # React-Select / custom dropdown option picker
    # ----------------------------------------------------------

    def select_option(self, locator, option_text: str):
        """
        Select an option from a React-Select or custom dropdown.

        Steps:
          1. Click the dropdown trigger (locator) to open the list.
          2. Wait for options to render.
          3. Find the option by exact or partial text match.
          4. Click it.

        Test Data = the option text to select e.g. "Staria"

        Works with:
          - React-Select (select__option class)
          - Creatable-Select
          - Custom ul/li dropdowns
          - Any dropdown where options render as clickable divs
        """
        def action():
            val = option_text.strip().lstrip("'")

            # ── Step 1: open the dropdown ──────────────────────
            self.wait.clickable(locator).click()
            time.sleep(0.5)

            # ── Step 2: find the option ────────────────────────
            option_xpaths = [
                # React-Select exact match
                f"//*[contains(@class,'select__option') and normalize-space(.)='{val}']",
                # React-Select partial match
                f"//*[contains(@class,'select__option') and contains(.,'{val}')]",
                # ARIA role option exact
                f"//*[@role='option' and normalize-space(.)='{val}']",
                # li exact
                f"//li[normalize-space(.)='{val}']",
                # Any menu item
                f"//*[contains(@class,'menu')]//*[normalize-space(.)='{val}']",
                f"//*[contains(@class,'option') and normalize-space(.)='{val}']",
                # Generic fallback
                f"//*[normalize-space(text())='{val}']",
            ]

            option_el = None
            for xpath in option_xpaths:
                try:
                    els = self.driver.find_elements(By.XPATH, xpath)
                    # Filter to only visible elements
                    visible = [e for e in els if e.is_displayed()]
                    if visible:
                        option_el = visible[0]
                        logger.info(
                            f"  [select_option] found '{val}' via: {xpath[:60]}"
                        )
                        break
                except Exception:
                    continue

            # ── Step 3: scroll into view and click ────────────
            if not option_el:
                raise RuntimeError(
                    f"select_option: could not find option '{val}'. "
                    f"Make sure the dropdown is open and the text matches exactly."
                )

            self.driver.execute_script(
                "arguments[0].scrollIntoView({{block:'nearest'}});",
                option_el
            )
            time.sleep(0.1)
            option_el.click()
            logger.info(f"  [select_option] selected '{val}'")

        return self.safe_execute(action, "select_option")

    # ----------------------------------------------------------
    # Time slot picker
    # ----------------------------------------------------------

    def select_time(self, locator, time_str: str):
        """
        Select a time from a custom scrollable dropdown list.

        time_str format: HH:MM AM/PM  e.g. "11:15 PM" or "09:30 AM"

        Steps:
          1. Click the time dropdown trigger (locator) to open it.
          2. Search the visible option list for an exact text match.
          3. If not visible, scroll the dropdown list until found.
          4. Click the matching time slot.

        Works with:
          - React-Select / Creatable-Select style dropdowns
          - Custom div/ul/li option lists
          - Any dropdown where options are rendered as clickable text rows
        """
        def action():
            # Strip apostrophe Excel may have added
            time_val = time_str.strip().lstrip("'")

            # ── Step 1: open the dropdown ─────────────────────
            trigger = self.wait.clickable(locator)
            trigger.click()
            time.sleep(0.6)

            # If dropdown didn't open, try clicking the dropdown
            # indicator arrow (▼) next to the trigger
            menu_open = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class,'menu') or "
                "contains(@class,'option') or "
                "@role='listbox' or @role='option']"
            )
            if not menu_open:
                try:
                    # Try the parent container
                    parent = self.driver.execute_script(
                        "return arguments[0].parentElement;", trigger
                    )
                    parent.click()
                    time.sleep(0.4)
                except Exception:
                    pass

            # Log visible options to help debug format mismatches
            visible_options = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class,'option')] | "
                "//*[@role='option'] | "
                "//li[contains(@class,'option')]"
            )
            if visible_options:
                sample = [o.text.strip() for o in visible_options[:5] if o.text.strip()]
                logger.info(
                    f"  [select_time] dropdown open — sample options: {sample}"
                )

            # ── Step 2: find the option by text ───────────────
            # Try common option container patterns used by
            # React-Select, custom dropdowns, and native lists
            option_xpaths = [
                # React-Select / Creatable-Select option (exact)
                f"//*[contains(@class,'option') and normalize-space(text())='{time_val}']",
                # React-Select option with child span
                f"//*[contains(@class,'option') and normalize-space(.)='{time_val}']",
                # li inside a dropdown menu
                f"//li[normalize-space(text())='{time_val}']",
                f"//li[normalize-space(.)='{time_val}']",
                # ARIA role option
                f"//*[@role='option' and normalize-space(text())='{time_val}']",
                f"//*[@role='option' and normalize-space(.)='{time_val}']",
                # Inside listbox
                f"//*[@role='listbox']//*[normalize-space(.)='{time_val}']",
                # Inside any menu container
                f"//*[contains(@class,'menu')]//*[normalize-space(.)='{time_val}']",
                # Generic fallback
                f"//*[normalize-space(text())='{time_val}']",
            ]

            option_el = None
            for xpath in option_xpaths:
                try:
                    els = self.driver.find_elements(By.XPATH, xpath)
                    if els:
                        option_el = els[0]
                        logger.info(
                            f"  [select_time] found '{time_val}' via: {xpath[:60]}"
                        )
                        break
                except Exception:
                    continue

            # ── Step 3: scroll inside dropdown if not found ───
            if not option_el:
                logger.info(
                    f"  [select_time] '{time_val}' not visible — scrolling dropdown"
                )
                # Find the scrollable dropdown container
                container_xpaths = [
                    "//*[contains(@class,'menu-list')]",
                    "//*[contains(@class,'dropdown-menu')]",
                    "//*[@role='listbox']",
                    "//*[contains(@class,'options')]",
                ]
                container = None
                for xpath in container_xpaths:
                    try:
                        els = self.driver.find_elements(By.XPATH, xpath)
                        if els:
                            container = els[0]
                            break
                    except Exception:
                        continue

                if container:
                    # Scroll in steps until the option appears
                    max_scrolls = 20
                    for _ in range(max_scrolls):
                        self.driver.execute_script(
                            "arguments[0].scrollTop += arguments[0].offsetHeight;",
                            container
                        )
                        time.sleep(0.15)
                        # Re-check after each scroll
                        for xpath in option_xpaths[:-1]:  # skip generic fallback
                            try:
                                els = self.driver.find_elements(By.XPATH, xpath)
                                if els:
                                    option_el = els[0]
                                    break
                            except Exception:
                                continue
                        if option_el:
                            break

            if not option_el:
                raise RuntimeError(
                    f"select_time: could not find time slot '{time_val}' "
                    "in the dropdown. Check the time format matches exactly "
                    "what is displayed (e.g. '11:15 PM' not '11:15PM')."
                )

            # ── Step 4: scroll option into view and click ─────
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'nearest'});",
                option_el
            )
            time.sleep(0.1)
            option_el.click()
            logger.info(f"  [select_time] selected '{time_val}'")

        return self.safe_execute(action, "select_time")

    # ----------------------------------------------------------
    # Toast / notification verifier
    # ----------------------------------------------------------

    def verify_toast(self, expected_text: str = ""):
        """
        Verify a green success toast notification appeared.

        expected_text (optional): if provided, checks that the toast
        message contains this text (case-insensitive).
        Pass empty string to only verify the toast appeared and is green.

        Raises on:
          - Toast not found within timeout
          - Toast found but background is not green
          - Toast text does not contain expected_text (when provided)
        """
        def action():
            # Common toast/notification container selectors
            toast_xpaths = [
                "//*[contains(@class,'toast')]",
                "//*[contains(@class,'notification')]",
                "//*[contains(@class,'alert')]",
                "//*[contains(@class,'snackbar')]",
                "//*[contains(@class,'Toastify')]",
                "//*[@role='alert']",
                "//*[@role='status']",
            ]

            toast_el = None
            for xpath in toast_xpaths:
                try:
                    els = WebDriverWait(self.driver, self.wait.timeout).until(
                        EC.visibility_of_element_located((By.XPATH, xpath))
                    )
                    toast_el = els
                    logger.info(
                        f"  [verify_toast] found toast via: {xpath}"
                    )
                    break
                except Exception:
                    continue

            if not toast_el:
                raise AssertionError(
                    "verify_toast: no toast/notification appeared "
                    f"within {self.wait.timeout}s after form submission."
                )

            # ── Check background colour is green ──────────────
            bg_color = toast_el.value_of_css_property("background-color")
            # background-color returns "rgba(r, g, b, a)" or "rgb(r, g, b)"
            # Green toast: G channel significantly higher than R and B
            # e.g. rgba(40, 167, 69, 1) or rgba(76, 175, 80, 1)
            import re as _re
            rgb = _re.findall(r"[\d.]+", bg_color)
            is_green = False
            if len(rgb) >= 3:
                r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
                # Green: G > 100, G > R*1.5, G > B*1.5
                is_green = g > 100 and g > r * 1.5 and g > b * 1.5

            if not is_green:
                raise AssertionError(
                    f"verify_toast: toast appeared but is NOT green. "
                    f"Background color: {bg_color}. "
                    "This may indicate an error toast instead of success."
                )

            # ── Check message text if provided ────────────────
            toast_text = toast_el.text.strip()
            logger.info(f"  [verify_toast] toast text: '{toast_text}'")

            if expected_text:
                if expected_text.upper() not in toast_text.upper():
                    raise AssertionError(
                        f"verify_toast: green toast appeared but text "
                        f"did not match.\n"
                        f"  Expected to contain: '{expected_text}'\n"
                        f"  Actual toast text:   '{toast_text}'"
                    )
                logger.info(
                    f"  [verify_toast] ✓ text matched: '{expected_text}'"
                )

            logger.info(
                f"  [verify_toast] ✓ green success toast verified"
                + (f": '{toast_text}'" if toast_text else "")
            )
            return toast_text

        return self.safe_execute(action, "verify_toast")

    # ----------------------------------------------------------
    # Quivers actions — ported from Quivers_Automation framework
    # ----------------------------------------------------------

    def js_click(self, locator):
        """JavaScript click — bypasses overlays, hidden inputs, CSS checkboxes."""
        def action():
            el = self.wait.present(locator)
            self.driver.execute_script("arguments[0].click();", el)
        return self.safe_execute(action, "js_click")

    def hover_and_click(self, locator):
        """Hover over element then click — for hover-reveal menus."""
        def action():
            el = self.driver.find_element(*locator)
            ActionChains(self.driver).move_to_element(el).click(el).perform()
        return self.safe_execute(action, "hover_and_click")

    def scroll_to_element(self, locator):
        """
        Scroll until the element is visible.

        ActionChains.move_to_element() calculates coordinates relative
        to the top-level viewport, so it throws "move target out of
        bounds" for elements inside iframes (e.g. legacy_panel_embed)
        because the element's rect is relative to the iframe document,
        not the page.

        Strategy (in order):
          1. scrollIntoView({block:'center'})  — works inside iframes
             because JS executes in whatever document context the
             driver is currently switched to.
          2. If the JS scroll raises (e.g. detached element), fall back
             to element.location_once_scrolled_into_view  — a WebDriver
             built-in that also works per-document.
          3. ActionChains.move_to_element() is intentionally NOT used.
        """
        def action():
            el = self.wait.present(locator)
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView("
                    "{block:'center', inline:'nearest'});",
                    el
                )
            except Exception:
                # Fallback: WebDriver built-in scroll (per-document)
                _ = el.location_once_scrolled_into_view
        return self.safe_execute(action, "scroll_to_element")

    def enter_text_slow(self, locator, text: str):
        """Type character by character — for fields needing slow input."""
        def action():
            el = self.wait.visible(locator)
            el.clear()
            for char in str(text):
                el.send_keys(char)
                time.sleep(0.3)
        return self.safe_execute(action, "enter_text_slow")

    def enter_text_keyenter(self, locator, text: str):
        """Type text then press Enter using ActionChains."""
        def action():
            el = self.wait.present(locator)
            ActionChains(self.driver).move_to_element(el)                .send_keys(str(text))                .send_keys(Keys.ENTER)                .perform()
        return self.safe_execute(action, "enter_text_keyenter")

    def enter_key_down(self, locator, _data: str = ""):
        """Press the DOWN arrow key on an element."""
        def action():
            el = self.wait.present(locator)
            ActionChains(self.driver).move_to_element(el)                .send_keys(Keys.DOWN).perform()
        return self.safe_execute(action, "enter_key_down")

    def enter_random_number(self, locator, digit_count: str = "6"):
        """Type a random N-digit number into a field."""
        import random as _random
        def action():
            n = int(digit_count)
            start = 10 ** (n - 1)
            end   = (10 ** n) - 1
            el = self.wait.present(locator)
            el.clear()
            el.send_keys(str(_random.randint(start, end)))
        return self.safe_execute(action, "enter_random_number")

    def edit_text(self, locator, text: str):
        """Clear field (Ctrl+A Delete) then type new text. Supports $VARCOUNTER$."""
        def action():
            val = str(text).strip().lstrip("'")
            el  = self.wait.present(locator)
            el.send_keys(Keys.CONTROL + "a")
            el.send_keys(Keys.DELETE)
            el.send_keys(val)
        return self.safe_execute(action, "edit_text")

    def accept_alert(self, _data: str = ""):
        """Accept a browser JavaScript alert/confirm dialog."""
        def action():
            self.driver.switch_to.alert.accept()
        return self.safe_execute(action, "accept_alert")

    def refresh(self, _data: str = ""):
        """Refresh the current browser page."""
        def action():
            self.driver.refresh()
        return self.safe_execute(action, "refresh")

    def zoom_out(self, zoom_level: str = "0.8"):
        """Zoom browser page. Test Data = zoom level e.g. 0.8 for 80%."""
        def action():
            self.driver.execute_script(
                f"document.body.style.zoom='{zoom_level}'"
            )
        return self.safe_execute(action, "zoom_out")

    def upload_file(self, locator, file_path: str):
        """Upload a file. Locator = file input element. Test Data = full file path."""
        def action():
            el = self.wait.present(locator)
            el.send_keys(str(file_path).strip().lstrip("'"))
        return self.safe_execute(action, "upload_file")

    def get_attribute(self, locator, attribute_name: str):
        """Read an HTML attribute value and log it."""
        def action():
            el  = self.driver.find_element(*locator)
            val = el.get_attribute(str(attribute_name))
            logger.info(f"  [get_attribute] {attribute_name}='{val}'")
            return str(val)
        return self.safe_execute(action, "get_attribute")

    def get_toast_text(self, locator, data: str = ""):
        """Read toast notification text and log it. Test Data = 'start:end' slice (optional)."""
        def action():
            el   = self.driver.find_element(*locator)
            text = el.text
            if data and ":" in str(data):
                parts = str(data).split(":")
                text  = text[int(parts[0]):int(parts[1])]
            logger.info(f"  [get_toast_text] toast='{text}'")
            return text
        return self.safe_execute(action, "get_toast_text")

    def check_text(self, locator, expected: str):
        """Verify element text contains expected string. Logs PASSED or FAILED."""
        def action():
            el   = self.driver.find_element(*locator)
            text = el.text
            if str(expected) in text:
                logger.info(f"  [check_text] PASSED — '{expected}' found in '{text}'")
            else:
                raise AssertionError(
                    f"check_text FAILED — '{expected}' not found in '{text}'"
                )
        return self.safe_execute(action, "check_text")

    def switch_to_active_window(self, _data: str = ""):
        """Switch to the most recently opened browser tab/window."""
        def action():
            WebDriverWait(self.driver, 40).until(
                EC.number_of_windows_to_be(2)
            )
            original = self.driver.current_window_handle
            new_wins  = [w for w in self.driver.window_handles if w != original]
            if new_wins:
                self.driver.switch_to.window(new_wins[-1])
                logger.info("  [switch_to_active_window] switched to new window")
        return self.safe_execute(action, "switch_to_active_window")

    def pop_up(self, locator):
        """Handle a popup — switch to active element and click it if present."""
        def action():
            self.driver.switch_to.active_element
            time.sleep(1)
            try:
                el = self.driver.find_element(*locator)
                if el:
                    el.click()
            except Exception:
                pass
        return self.safe_execute(action, "pop_up")

    def wait_for_element_click(self, locator, timeout: str = "20"):
        """Wait up to N seconds for element then click. Test Data = timeout seconds."""
        def action():
            t  = int(str(timeout).strip() or 20)
            el = WebDriverWait(self.driver, t).until(
                EC.presence_of_element_located(locator)
            )
            el.click()
        return self.safe_execute(action, "wait_for_element_click")

    def dropdown_menu_option(self, locator, option_text: str):
        """
        Click the trigger element to open a custom dropdown, then find
        and click the rendered option whose visible text matches
        option_text.

        Root cause of page-wide mis-matching:
          Searching the whole document with generic selectors like
          [role='option'] or li matches the FIRST visible dropdown on
          the page (e.g. a nav menu), not the one just opened.

        Fix — scoped search strategy (in order):
          1. Walk up from the trigger to find the nearest ancestor that
             contains newly-appeared option elements after the click.
             Ancestors tried: parent → grandparent → great-grandparent
             → body-level container with [role='listbox'|'menu'|
             'combobox'] → document as last resort.
          2. Within that container, probe option selectors in order:
               [role='option'], [role='listbox'] [role='option'],
               li (not nav/header li), .dropdown-item,
               [class*='option'], [class*='item']
          3. Newly-appeared elements are preferred — elements that were
             NOT visible before the trigger click are collected first,
             then fall back to all visible if none found.

        Text matching order:
          • exact strip  →  case-insensitive exact
          →  contains (case-insensitive)  →  innerHTML contains
        """
        OPTION_SELECTORS = [
            "[role='option']",
            "[role='listbox'] [role='option']",
            "li[role='option']",
            "li.select2-results__option",
            "ul.select2-results__options li",
            "ul.dropdown-menu li",
            ".dropdown-item",
            "[class*='option']:not(select)",
            "[class*='item']",
            "li:not(nav li):not(header li)",
        ]

        # Ancestor selectors to scope the search — tried in order
        CONTAINER_SELECTORS = [
            "[role='listbox']",
            "[role='menu']",
            "[role='combobox']",
            "[class*='dropdown'][class*='menu']",
            "[class*='select'][class*='menu']",
            "[class*='options']",
            "[class*='dropdown-content']",
        ]

        def _find_items_in(container):
            """Return visible option elements inside container."""
            for sel in OPTION_SELECTORS:
                try:
                    candidates = container.find_elements(
                        By.CSS_SELECTOR, sel
                    )
                    visible = [e for e in candidates if e.is_displayed()]
                    if visible:
                        return visible, sel
                except Exception:
                    continue
            return [], None

        def _match(items, val):
            """Return first item matching val, or None."""
            val_lower = val.lower()
            for item in items:
                if item.text.strip() == val:
                    return item
            for item in items:
                if item.text.strip().lower() == val_lower:
                    return item
            for item in items:
                if val_lower in item.text.strip().lower():
                    return item
            for item in items:
                if val_lower in (
                    item.get_attribute("innerHTML") or ""
                ).lower():
                    return item
            return None

        def action():
            val = str(option_text).strip().lstrip("'")

            # 1. Snapshot currently-visible elements before click
            #    so we can identify newly-appeared containers
            before_ids = {
                e.id for e in self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ",".join(CONTAINER_SELECTORS)
                )
                if e.is_displayed()
            }

            # 2. Click trigger
            trigger = self.wait.clickable(locator)
            trigger.click()
            time.sleep(0.5)

            # 3. Look for a container that appeared AFTER the click
            items       = []
            used_sel    = None
            used_cont   = "page"

            after_containers = [
                e for e in self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ",".join(CONTAINER_SELECTORS)
                )
                if e.is_displayed() and e.id not in before_ids
            ]

            for cont in after_containers:
                items, used_sel = _find_items_in(cont)
                if items:
                    used_cont = cont.tag_name + (
                        cont.get_attribute("class") or ""
                    )[:40]
                    break

            # 4. If no new container found, walk up trigger's ancestors
            if not items:
                el = trigger
                for _ in range(5):
                    try:
                        el = el.find_element(By.XPATH, "..")
                        items, used_sel = _find_items_in(el)
                        if items:
                            used_cont = f"ancestor<{el.tag_name}>"
                            break
                    except Exception:
                        break

            # 5. Last resort — page-wide search but EXCLUDE items
            #    that were already visible before the click
            if not items:
                for sel in OPTION_SELECTORS:
                    candidates = self.driver.find_elements(
                        By.CSS_SELECTOR, sel
                    )
                    visible = [e for e in candidates if e.is_displayed()]
                    if visible:
                        items    = visible
                        used_sel = sel
                        used_cont = "page (fallback)"
                        break

            if not items:
                raise RuntimeError(
                    f"dropdown_menu_option: no option elements found "
                    f"after clicking trigger for '{val}'"
                )

            logger.info(
                f"  [dropdown_menu_option] {len(items)} options in "
                f"'{used_cont}' via '{used_sel}'"
            )

            # 6. Match and click
            match = _match(items, val)
            if match:
                match.click()
                return

            available = [i.text.strip() for i in items[:10]]
            raise RuntimeError(
                f"dropdown_menu_option: option '{val}' not found. "
                f"Available (first 10): {available}"
            )

        return self.safe_execute(action, "dropdown_menu_option")

    def filter_dropdown_list(self, locator, filter_value: str):
        """Open a select2-style dropdown and click the matching option."""
        def action():
            val    = str(filter_value).strip().lstrip("'")
            expand = self.driver.find_element(*locator).get_attribute("aria-expanded")
            if expand == "false":
                self.driver.find_element(*locator).click()
                time.sleep(1)
            items = self.driver.find_elements(By.CSS_SELECTOR, "li.select2-results__option")
            for item in items:
                if val == item.get_attribute("innerHTML"):
                    item.click()
                    return
            raise RuntimeError(f"filter_dropdown_list: option '{val}' not found")
        return self.safe_execute(action, "filter_dropdown_list")

    def enter_text_select_first_option(self, locator, text: str):
        """Type into autocomplete field then press Enter to select first option."""
        def action():
            val = str(text).strip().lstrip("'")
            el  = self.driver.find_element(*locator)
            ActionChains(self.driver)                .move_to_element(el).click()                .send_keys(val)                .send_keys(Keys.ENTER)                .perform()
        return self.safe_execute(action, "enter_text_select_first_option")

    def enter_value_from_dropdown(self, locator, text: str):
        """Click dropdown, type text, press Enter — for searchable dropdowns."""
        def action():
            val = str(text).strip().lstrip("'")
            el  = self.driver.find_element(*locator)
            ActionChains(self.driver)                .move_to_element(el).click()                .send_keys(val)                .send_keys(Keys.ENTER)                .perform()
        return self.safe_execute(action, "enter_value_from_dropdown")

    def enter_value_multi_first_option(self, locator, _data: str = ""):
        """Click multi-select dropdown and pick the first available option."""
        def action():
            el = self.driver.find_element(*locator)
            ActionChains(self.driver).move_to_element(el).click().perform()
            try:
                first = self.driver.find_element(By.ID, "downshift-1-item-0")
                first.click()
            except Exception:
                options = self.driver.find_elements(
                    By.XPATH,
                    "//*[@role='option'] | //*[contains(@class,'option')]"
                )
                if options:
                    options[0].click()
        return self.safe_execute(action, "enter_value_multi_first_option")

    def drag_drop(self, locator, target_xpath: str):
        """Drag element (locator) and drop onto target_xpath. Test Data = target XPath."""
        def action():
            source = self.driver.find_element(*locator)
            target = self.driver.find_element(By.XPATH, str(target_xpath).strip().lstrip("'"))
            ActionChains(self.driver).drag_and_drop(source, target).perform()
        return self.safe_execute(action, "drag_drop")

    def log_in_file(self, text: str = ""):
        """Write a custom message to the step results log."""
        def action():
            logger.info(f"  [log_in_file] {text}")
            step_logger.info(f"LOG | {text}")
        return self.safe_execute(action, "log_in_file")

    def enter_totp(self, secret_key: str):
        """
        Generate and enter a TOTP 2FA code from a secret key.
        Requires: pip install pyotp
        Test Data = the TOTP secret key e.g. HJBGC22SJIWDILZ4...
        Enters each digit into separate code_1, code_2 ... fields.
        """
        def action():
            try:
                import pyotp
            except ImportError:
                raise RuntimeError(
                    "pyotp not installed. Run: pip install pyotp"
                )
            key      = str(secret_key).strip().lstrip("'")
            otp_code = pyotp.TOTP(key).now()
            logger.info(f"  [enter_totp] generated OTP (hidden for security)")
            for i, digit in enumerate(otp_code, start=1):
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, f"code_{i}"))
                )
                field.clear()
                field.send_keys(digit)
                time.sleep(0.2)
            logger.info("  [enter_totp] OTP entered successfully")
        return self.safe_execute(action, "enter_totp")

    # ----------------------------------------------------------
    # General-purpose CSV data store
    # ----------------------------------------------------------
    #
    # SAVE_TO_CSV   — capture an element's text and write it to a
    #                 named CSV file under the data/ folder.
    # READ_FROM_CSV — look up a value from that CSV by label and
    #                 type it into a field.
    #
    # Test Data format for both actions:
    #
    #   "label"                       → file = data/shared.csv
    #   "label | filename.csv"        → file = data/filename.csv
    #   "label | filename.csv | col"  → read from named column
    #                                   (SAVE_TO_CSV: ignored)
    #
    # CSV format written by SAVE_TO_CSV:
    #   Timestamp  | Label          | Value
    #   2024-01-15 | order_number   | O26156_USACA_893C2700
    #
    # Example CSV usage:
    #
    #   # Module A — capture order number after creating order
    #   Action             : SAVE_TO_CSV
    #   Locator            : XPATH  //h2[@class='order-id']
    #   Test Data          : order_number | orders.csv
    #
    #   # Module B — use captured order number in search field
    #   Action             : READ_FROM_CSV
    #   Locator            : XPATH  //input[@placeholder='Search']
    #   Test Data          : order_number | orders.csv
    #
    # ----------------------------------------------------------

    @staticmethod
    def _parse_csv_test_data(test_data: str):
        """
        Parse the Test Data field for SAVE_TO_CSV / READ_FROM_CSV.

        Returns (label, filepath, column_name_or_none).

        Formats accepted:
          "label"
          "label | filename.csv"
          "label | filename.csv | ColumnName"
        """
        import csv as _csv
        parts     = [p.strip() for p in str(test_data).split("|")]
        label     = parts[0] if len(parts) > 0 else ""
        filename  = parts[1] if len(parts) > 1 else "shared.csv"
        col_name  = parts[2] if len(parts) > 2 else None

        if not filename.endswith(".csv"):
            filename += ".csv"

        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)

        return label.strip(), filepath, col_name

    def save_to_csv(self, locator, test_data: str):
        """
        SAVE_TO_CSV — capture element text and store it in a CSV
        so other modules can look it up by label.

        Test Data: "label"  or  "label | filename.csv"

        Writes a row:  Timestamp | Label | Value
        If the label already exists in the file the old row is
        updated rather than creating a duplicate.
        """
        def action():
            import csv as _csv

            label, filepath, _ = self._parse_csv_test_data(test_data)

            el  = self.wait.visible(locator)
            val = (el.text or el.get_attribute("value") or "").strip()

            # Read existing rows
            existing = []
            if os.path.exists(filepath):
                with open(filepath, "r", newline="", encoding="utf-8") as f:
                    existing = list(_csv.reader(f))

            # Update existing label or append new row
            ts      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = False
            for row in existing:
                if len(row) >= 2 and row[1].strip() == label:
                    row[0] = ts
                    if len(row) >= 3:
                        row[2] = val
                    else:
                        row.append(val)
                    updated = True
                    break

            if not updated:
                existing.append([ts, label, val])

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                _csv.writer(f).writerows(existing)

            # Also store in shared_store for same-session use
            self.context.shared_store[label] = val

            logger.info(
                f"  [save_to_csv] '{label}' = '{val}' → {filepath}"
            )

        return self.safe_execute(action, "save_to_csv")

    def read_from_csv(self, locator, test_data: str):
        """
        READ_FROM_CSV — look up the LATEST value for a label in a
        CSV data file and type it into the field at locator.

        Test Data column in your module CSV:
          Just the label name — nothing else required.

            Test Data : order_number

          Optional — specify a different file (default: data/shared.csv):

            Test Data : order_number | orders.csv

        CSV file format (written by SAVE_TO_CSV):
          Two columns with headers:   Label  |  Value
          Multiple rows for the same label are allowed — the LAST
          row matching the label is used (most recent run wins).

        The value is also stored in shared_store["last_csv_value"]
        so subsequent steps can reference it without re-reading the file.
        """
        def action():
            import csv as _csv

            label, filepath, _ = self._parse_csv_test_data(test_data)

            if not label:
                raise ValueError(
                    "read_from_csv: Test Data must contain a label. "
                    "Example: 'order_number'  or  'order_number | orders.csv'"
                )

            value = None

            # 1. Check in-memory shared_store first (same-session fast path)
            if label in self.context.shared_store:
                value = str(self.context.shared_store[label])
                logger.info(
                    f"  [read_from_csv] '{label}' from shared_store "
                    f"= '{value}'"
                )

            # 2. Read from CSV file — always scan ALL rows and keep
            #    the LAST match so the most recent run's value is used
            if value is None:
                if not os.path.exists(filepath):
                    raise RuntimeError(
                        f"read_from_csv: file not found: {filepath}\n"
                        f"  Run SAVE_TO_CSV with label '{label}' first."
                    )

                with open(filepath, newline="", encoding="utf-8") as f:
                    sample = f.read(1024)
                    f.seek(0)

                    # Detect whether the file has a header row
                    has_header = (
                        "Label" in sample or
                        "label" in sample or
                        "Value" in sample
                    )

                    if has_header:
                        # Headed format: Label | Value  (+ optional Timestamp)
                        reader = _csv.DictReader(f)
                        # Normalise header keys to lowercase for safety
                        for row in reader:
                            norm = {k.strip().lower(): v.strip()
                                    for k, v in row.items()}
                            if norm.get("label") == label.lower() or \
                               norm.get("label") == label:
                                # Keep scanning — we want the LAST match
                                value = norm.get("value", "")
                    else:
                        # Headerless 3-column format:
                        # Timestamp | Label | Value
                        reader = _csv.reader(f)
                        for row in reader:
                            if len(row) >= 3 and row[1].strip() == label:
                                value = row[2].strip()
                            elif len(row) >= 2 and row[0].strip() == label:
                                value = row[1].strip()

                if value is None:
                    raise RuntimeError(
                        f"read_from_csv: label '{label}' not found "
                        f"in {filepath}"
                    )

            # Store for downstream steps
            self.context.shared_store["last_csv_value"] = value
            self.context.shared_store[label] = value

            logger.info(f"  [read_from_csv] '{label}' = '{value}'")

            el = self.wait.present(locator)
            el.clear()
            el.send_keys(value)

        return self.safe_execute(action, "read_from_csv")

    # ── Legacy aliases — kept for backward compatibility ───────

    def fill_order_id_from_csv(self, locator, test_step: str):
        """Legacy alias → read_from_csv using data/orders.csv"""
        return self.read_from_csv(
            locator,
            f"{test_step} | orders.csv"
        )

    def get_attribute_save_csv(self, locator, label: str):
        """Legacy alias → save_to_csv using data/orders.csv"""
        return self.save_to_csv(
            locator,
            f"{label} | orders.csv"
        )

    def switch_to_shadow_root(self, locator):
        """Switch context into a Shadow DOM host element."""
        def action():
            self._shadow_host = self.wait.present(locator)
            logger.info("  [switch_to_shadow_root] shadow host stored")
        return self.safe_execute(action, "switch_to_shadow_root")

    def enter_text_in_shadow(self, _locator, data: str):
        """
        Type into a Shadow DOM input.
        Locator Value = CSS selector of the input inside the shadow root.
        Requires SWITCH_TO_SHADOW_ROOT to have been called first.
        """
        def action():
            if not hasattr(self, "_shadow_host"):
                raise RuntimeError(
                    "enter_text_in_shadow: call SWITCH_TO_SHADOW_ROOT first"
                )
            css = _locator[1] if isinstance(_locator, tuple) else str(_locator)
            el  = self.driver.execute_script(
                "return arguments[0].shadowRoot.querySelector(arguments[1])",
                self._shadow_host, css
            )
            el.click()
            el.send_keys(Keys.CONTROL + "a")
            el.send_keys(Keys.DELETE)
            el.send_keys(str(data).strip().lstrip("'"))
        return self.safe_execute(action, "enter_text_in_shadow")

    def click_in_shadow(self, _locator, _data: str = ""):
        """
        Click an element inside a Shadow DOM.
        Locator Value = CSS selector inside the shadow root.
        Requires SWITCH_TO_SHADOW_ROOT to have been called first.
        """
        def action():
            if not hasattr(self, "_shadow_host"):
                raise RuntimeError(
                    "click_in_shadow: call SWITCH_TO_SHADOW_ROOT first"
                )
            css = _locator[1] if isinstance(_locator, tuple) else str(_locator)
            el  = self.driver.execute_script(
                "return arguments[0].shadowRoot.querySelector(arguments[1])",
                self._shadow_host, css
            )
            el.click()
        return self.safe_execute(action, "click_in_shadow")

    def get_list(self, locator, _data: str = ""):
        """
        Read all rows from a table/list and log them.
        Logs each row to step_results log.
        """
        def action():
            rows = self.driver.find_elements(*locator)
            logger.info(f"  [get_list] found {len(rows)} rows")
            for i, row in enumerate(rows, 1):
                step_logger.info(f"LIST_ROW {i} | {row.text.strip()}")
        return self.safe_execute(action, "get_list")

    def get_table(self, locator, _data: str = ""):
        """
        Read a full HTML table and log all rows + columns.
        """
        def action():
            table  = self.driver.find_element(*locator)
            rows   = table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"  [get_table] found {len(rows)} rows")
            for i, row in enumerate(rows):
                cols = [c.text.strip() for c in row.find_elements(By.XPATH, "td|th")]
                step_logger.info(f"TABLE_ROW {i} | {' | '.join(cols)}")
        return self.safe_execute(action, "get_table")

    def records_per_page(self, locator, value: str):
        """Set records-per-page dropdown in a paginated table."""
        def action():
            val = str(value).strip().lstrip("'")
            self.driver.find_element(*locator).click()
            time.sleep(0.5)
            options = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class,'option') or @role='option']"
            )
            for opt in options:
                if opt.text.strip() == val:
                    opt.click()
                    return
            raise RuntimeError(
                f"records_per_page: option '{val}' not found in dropdown"
            )
        return self.safe_execute(action, "records_per_page")

    # ----------------------------------------------------------
    # iFrame
    # ----------------------------------------------------------

    def switch_to_iframe(self, locator):
        def action():
            iframe = self.wait.present(locator)
            self.driver.switch_to.frame(iframe)
        return self.safe_execute(action, "switch_to_iframe")

    def switch_out_iframe(self):
        def action():
            self.driver.switch_to.default_content()
        return self.safe_execute(action, "switch_out_iframe")

    # ----------------------------------------------------------
    # Recording markers
    # ----------------------------------------------------------

    def start_recording(self, label: str = None):
        """Stub – replace with real recording logic if needed."""
        self.context.recording_active = True
        logger.info(
            "Recording started" + (f": {label}" if label else "")
        )

    def stop_recording(self, label: str = None):
        """Stub – replace with real recording logic if needed."""
        self.context.recording_active = False
        logger.info(
            "Recording stopped" + (f": {label}" if label else "")
        )

    # ----------------------------------------------------------
    # External script runner
    # ----------------------------------------------------------

    def run_script(self, script_input: str):
        """
        RUN_SCRIPT action — executes an external Python file.

        CSV usage:
          Action    : RUN_SCRIPT
          Test Data : filename.py          ← just the filename, looked
                                             up in config.scripts_path
                      OR
                      /absolute/path/to/script.py   ← used as-is

        The script runs in a subprocess with the same Python
        interpreter.  The current driver session is passed via
        environment variables so the script can reconnect if needed:
          SELENIUM_SESSION_ID  — the active Chrome session ID
          SELENIUM_REMOTE_URL  — the remote debugger URL

        stdout/stderr from the script is captured and logged.
        A non-zero exit code raises an exception (marks step FAIL).
        """
        import subprocess, sys

        if not script_input:
            raise ValueError("RUN_SCRIPT: no script specified in Test Data")

        # Resolve full path
        if os.path.isabs(script_input):
            script_path = script_input
        else:
            script_path = os.path.join(
                self.config.scripts_path,
                script_input
            )

        if not os.path.exists(script_path):
            raise FileNotFoundError(
                f"RUN_SCRIPT: script not found: {script_path}"
            )

        logger.info(f"RUN_SCRIPT: running → {script_path}")

        # Pass session info so the script can attach to the
        # running browser if needed.
        env = os.environ.copy()
        try:
            env["SELENIUM_SESSION_ID"] = self.driver.session_id or ""
            env["SELENIUM_REMOTE_URL"] = (
                self.driver.command_executor._url
                if hasattr(self.driver.command_executor, "_url")
                else ""
            )
        except Exception:
            pass   # Non-critical — script may not need it

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            env=env,
        )

        if result.stdout:
            for line in result.stdout.strip().splitlines():
                logger.info(f"  [script stdout] {line}")

        if result.stderr:
            for line in result.stderr.strip().splitlines():
                logger.warning(f"  [script stderr] {line}")

        if result.returncode != 0:
            raise RuntimeError(
                f"RUN_SCRIPT: '{script_input}' exited with "
                f"code {result.returncode}"
            )

        logger.info(
            f"RUN_SCRIPT: '{script_input}' completed successfully"
        )


# =========================================================
# SMART LOCATOR RESOLVER
# =========================================================
#
# Resolution order (when smart_locator=True):
#   1. Text / ARIA auto-discovery  — finds elements by visible
#      text, placeholder, aria-label, id, title, or name attr.
#   2. AI Vision fallback          — screenshots the page and
#      asks Claude to identify the best locator.
#   3. Hard failure                — raises with a clear message.
#
# When smart_locator=False the engine uses the CSV Locator /
# Locator Value columns exactly as before (no change in behaviour).
# =========================================================

class SmartLocatorResolver:

    def __init__(self, driver, config: "FrameworkConfig"):
        self.driver = driver
        self.config = config

    # ----------------------------------------------------------
    # Public entry point
    # ----------------------------------------------------------

    def _clean_description(self, description: str) -> str:
        """
        Extract the core element label from a Basic Sanity description.
        Regex compiled inline to avoid Python 3.11 class-body scope issues.

        Examples:
          "Click Button 'Sign In'"      -> 'Sign In'
          "Click Link 'All Bookings'"   -> 'All Bookings'
          "Enter text in username"      -> 'username'
          "Sign In"                     -> 'Sign In'  (unchanged)
        """
        import re  # ensure re is in local scope
        d = description.strip()

        # Extract text inside quotes — handles Click Button 'Sign In'
        m = re.search(r"(?:[\"\']{1})(.*?)(?:[\"\']{1})", d)
        if m:
            return m.group(1).strip()

        # Strip leading action + role words
        # e.g. 'Click the Login button' -> 'Login button'
        pat = re.compile(
            r"^(?:"
            r"click\s+(?:the\s+)?(?:button|link|menu|item|tab|icon|"
            r"checkbox|radio|dropdown|option|element|nav|navigation)\s*"
            r"|double[\s-]click\s+(?:the\s+)?"
            r"|enter\s+(?:the\s+)?(?:text|value|data)\s*"
            r"|navigate\s+to\s+"
            r"|open\s+(?:the\s+)?(?:url|page|link)\s*"
            r")",
            re.IGNORECASE
        )
        cleaned = pat.sub("", d).strip()
        if cleaned and cleaned.lower() != d.lower():
            return cleaned

        return d


    def resolve(self, description: str):
        """
        Return a (By, value) locator tuple for `description`.
        Tries text/ARIA strategies first; falls back to AI Vision
        if enabled and all text strategies fail.
        """
        # Clean the description — strip action words like "Click Button"
        # so "Click Button 'Sign In'" → "Sign In" for page matching
        cleaned = self._clean_description(description)
        if cleaned != description:
            logger.info(
                f"  [SmartLocator] description cleaned: "
                f"'{description}' → '{cleaned}'"
            )

        locator = self._try_text_strategies(cleaned)
        # If cleaned description fails, also try original as fallback
        if not locator and cleaned != description:
            locator = self._try_text_strategies(description)

        if locator:
            logger.info(
                f"  [SmartLocator] found via text/ARIA: {locator}"
            )
            return locator

        if self.config.ai_locator_fallback and _ANTHROPIC_AVAILABLE:
            logger.info(
                f"  [SmartLocator] text/ARIA failed — trying AI Vision"
            )
            locator = self._try_ai_vision(description)

        if locator:
            logger.info(
                f"  [SmartLocator] found via AI Vision: {locator}"
            )
            return locator

        raise RuntimeError(
            f"SmartLocator could not find element for: '{description}'. "
            "Add Locator + Locator Value to the CSV row to pin it manually."
        )

    # ----------------------------------------------------------
    # Strategy 1 — text / ARIA discovery
    # ----------------------------------------------------------

    def _try_text_strategies(self, description: str):
        """
        Try a chain of XPath expressions that match by visible
        content or accessibility attributes.  Returns the first
        (By, xpath) pair whose element exists in the DOM, or None.
        """
        d = description.replace("'", "\'")   # escape for XPath

        candidates = [
            # ── Scoped to sidebar/nav first ───────────────────
            # Prevents matching page headings, breadcrumbs, table
            # cells that also contain the same text as a nav link.
            f"//nav//a[normalize-space(.)='{d}']",
            f"//aside//a[normalize-space(.)='{d}']",
            f"//*[contains(@class,'sidebar') or contains(@class,'sidenav') or "
            f"contains(@class,'side-menu') or contains(@class,'nav-menu') or "
            f"contains(@class,'main-menu')]//a[normalize-space(.)='{d}']",
            f"//*[contains(@class,'sidebar') or contains(@class,'sidenav') or "
            f"contains(@class,'side-menu') or contains(@class,'nav-menu') or "
            f"contains(@class,'main-menu')]//*[normalize-space(.)='{d}']",
            f"//*[@role='menuitem' and normalize-space(.)='{d}']",
            f"//*[@role='navigation']//a[normalize-space(.)='{d}']",
            # ── Exact visible text (direct text node) ─────────
            f"//*[normalize-space(text())='{d}']",
            # ── Exact full text including child elements ───────
            # Handles React/styled buttons where text is in <span>
            f"//*[normalize-space(.)='{d}']",
            # ── Attribute-based matches ────────────────────────
            f"//*[@placeholder='{d}']",
            f"//*[@aria-label='{d}']",
            f"//*[@id='{d}']",
            f"//*[@name='{d}']",
            f"//*[@title='{d}']",
            f"//input[@value='{d}']",
            # ── Partial matches (fallback) ─────────────────────
            f"//nav//*[contains(normalize-space(.),'{d}')]",
            f"//aside//*[contains(normalize-space(.),'{d}')]",
            f"//*[contains(normalize-space(.),'{d}') and not(self::html) and not(self::body) and not(self::div[@id])]",
            f"//*[contains(normalize-space(text()),'{d}')]",
            f"//*[contains(@placeholder,'{d}')]",
            f"//*[contains(@aria-label,'{d}')]",
        ]

        for xpath in candidates:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    return (By.XPATH, xpath)
                else:
                    logger.debug(
                        f"  [SmartLocator] 0 elements for: {xpath[:80]}"
                    )
            except Exception as e:
                logger.debug(
                    f"  [SmartLocator] XPath error: {xpath[:80]} | {e}"
                )
                continue

        # Last resort — take a screenshot so the team can see what
        # the page looks like when smart locator fails
        try:
            from datetime import datetime as _dt
            ts   = _dt.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshots/smartlocator_fail_{ts}.png"
            self.driver.save_screenshot(path)
            logger.warning(
                f"  [SmartLocator] all strategies failed for: '{description}'. "
                f"Page screenshot saved: {path}"
            )
        except Exception:
            pass

        return None

    # ----------------------------------------------------------
    # Strategy 2 — AI Vision via Claude API
    # ----------------------------------------------------------

    def _try_ai_vision(self, description: str):
        """
        Take a screenshot, send it to Claude with the element
        description, and parse back a (By, value) locator.
        Returns None if the API call fails or returns nothing useful.
        """
        import re  # ensure re is in local scope
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not api_key:
            logger.warning(
                "AI Vision fallback skipped: ANTHROPIC_API_KEY not set"
            )
            return None

        try:
            screenshot_b64 = self.driver.get_screenshot_as_base64()
            page_source    = self.driver.page_source[:8000]  # trim for token limit

            client = _anthropic_lib.Anthropic(api_key=api_key)

            prompt = (
                f"You are a Selenium test automation expert.\n"
                f"Given the screenshot and partial HTML below, return the "
                f"single best CSS selector or XPath to locate this element:\n"
                f"  Element description: '{description}'\n\n"
                f"Rules:\n"
                f"- Prefer CSS selectors; use XPath only if necessary.\n"
                f"- Return ONLY a JSON object, nothing else:\n"
                f"  {{\"type\": \"CSS_SELECTOR\", \"value\": \"...\"}}"
                f"  or {{\"type\": \"XPATH\", \"value\": \"...\"}}\n\n"
                f"Partial HTML:\n{page_source}"
            )

            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=256,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type":       "base64",
                                    "media_type": "image/png",
                                    "data":       screenshot_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            import json, re
            raw  = response.content[0].text.strip()
            # Strip markdown fences if present
            raw  = re.sub(r"```[a-z]*", "", raw).strip().strip("`")
            data = json.loads(raw)

            loc_type  = data.get("type",  "").strip().upper()
            loc_value = data.get("value", "").strip()

            if not loc_type or not loc_value:
                logger.warning("AI Vision returned empty locator")
                return None

            by_map = {
                "CSS_SELECTOR": By.CSS_SELECTOR,
                "XPATH":        By.XPATH,
                "ID":           By.ID,
                "NAME":         By.NAME,
            }

            by = by_map.get(loc_type)

            if not by:
                logger.warning(
                    f"AI Vision returned unsupported type: {loc_type}"
                )
                return None

            # Verify the element actually exists before trusting it
            elements = self.driver.find_elements(by, loc_value)

            if elements:
                return (by, loc_value)

            logger.warning(
                f"AI Vision locator not found in DOM: {loc_type}={loc_value}"
            )
            return None

        except Exception as e:
            logger.warning(f"AI Vision locator failed: {e}")
            return None


# =========================================================
# ACTION ENGINE
# =========================================================

class ActionEngine:

    # Actions that need only Test Data (no locator).
    NO_LOCATOR = {
        "OPEN_URL",
        "TAKE_SCREENSHOT",
        "SLEEP",
        "START_RECORDING",
        "STOP_RECORDING",
        "VERIFY_TOAST",     # Test Data = expected text (optional)
        "WAIT_FOR_URL",     # Test Data = partial URL to wait for (optional)
        "PAUSE",            # Test Data = optional message to display
        "ACCEPT_JAVASCRIPT_ALERT",
        "REFRESH",
        "ZOOM_OUT",
        "SWITCH_TO_ACTIVE_WINDOW",
        "LOG_IN_FILE",
        "ENTER_TOTP",
        "RUN_SCRIPT",       # Test Data = script filename or absolute path
    }

    # Actions that need no arguments at all.
    NO_ARGS = {
        "SCROLL_DOWN",
        "SWITCH_OUT_IFRAME",
    }

    def __init__(self, web: WebActions, config: "FrameworkConfig" = None):

        self.web      = web
        self.config   = config or FrameworkConfig()
        self.resolver = SmartLocatorResolver(web.driver, self.config)

        self.registry = {
            "CLICK":                      web.click,
            "DOUBLE_CLICK":               web.double_click,
            "ENTER_TEXT":                 web.enter_text,
            "ENTER_TEXT_ENTER":           web.enter_text_enter,
            "ENTER_TEXT_WITH_TIMESTAMP":  web.enter_text_with_timestamp,
            "CLEAR_TEXT":                 web.clear_text,
            "PRESS_ENTER":                web.press_enter,
            "GET_TEXT":                   web.get_text,
            "OPEN_URL":                   web.open_url,
            "SCROLL_DOWN":                web.scroll_down,
            "TAKE_SCREENSHOT":            web.screenshot,
            "SLEEP":                      web.sleep,
            "SWITCH_TO_IFRAME":           web.switch_to_iframe,
            "SWITCH_OUT_IFRAME":          web.switch_out_iframe,
            "START_RECORDING":            web.start_recording,
            "STOP_RECORDING":             web.stop_recording,
            "SELECT_DATE":                web.select_date,
            "SELECT_TIME":                web.select_time,
            "SELECT_OPTION":              web.select_option,
            # ── Quivers actions ────────────────────────────────
            "JS_CLICK":                       web.js_click,
            "DOUBLECLICK":                    web.double_click,
            "HOVER_AND_CLICK":                web.hover_and_click,
            "SCROLL_TO_ELEMENT":              web.scroll_to_element,
            "ENTER_TEXT_SLOW":                web.enter_text_slow,
            "ENTER_TEXT_KEYENTER":            web.enter_text_keyenter,
            "ENTER_KEY_DOWN":                 web.enter_key_down,
            "ENTER_RANDOM_NUMBER":            web.enter_random_number,
            "EDIT_TEXT":                      web.edit_text,
            "ACCEPT_JAVASCRIPT_ALERT":        web.accept_alert,
            "REFRESH":                        web.refresh,
            "ZOOM_OUT":                       web.zoom_out,
            "UPLOAD_FILE":                    web.upload_file,
            "GET_ATTRIBUTE":                  web.get_attribute,
            "GET_ATTRIBUTE_SAVE_CSV":         web.get_attribute_save_csv,
            "SAVE_TO_CSV":                    web.save_to_csv,
            "READ_FROM_CSV":                  web.read_from_csv,
            "GET_TOAST_TEXT":                 web.get_toast_text,
            "CHECK_TEXT_IN_STRING":           web.check_text,
            "SWITCH_TO_ACTIVE_WINDOW":        web.switch_to_active_window,
            "POP_UP":                         web.pop_up,
            "WAIT_FOR_ELEMENT_CLICK":         web.wait_for_element_click,
            "DROPDOWN_MENU_OPTION":           web.dropdown_menu_option,
            "FILTER_DROPDOWN_LIST":           web.filter_dropdown_list,
            "ENTER_TEXT_SELECT_FIRST_DROPDOWN_OPTION": web.enter_text_select_first_option,
            "ENTER_VALUE_FROM_DROPDOWN_OPTIONS": web.enter_value_from_dropdown,
            "ENTER_VALUE_MULTI_SELECTION_FIRST_OPTION": web.enter_value_multi_first_option,
            "DRAG_DROP":                      web.drag_drop,
            "LOG_IN_FILE":                    web.log_in_file,
            "ENTER_TOTP":                     web.enter_totp,
            "FILL_ORDER_ID_FROM_CSV":         web.fill_order_id_from_csv,
            "SWITCH_TO_SHADOW_ROOT":          web.switch_to_shadow_root,
            "ENTER_TEXT_IN_SHADOW":           web.enter_text_in_shadow,
            "CLICK_IN_SHADOW":                web.click_in_shadow,
            "GET_LIST":                       web.get_list,
            "GET_TABLE":                      web.get_table,
            "RECORDS_PER_PAGE":               web.records_per_page,
            "VERIFY_TOAST":               web.verify_toast,
            "WAIT_FOR_URL":               web.wait_for_url,
            "WAIT_FOR_ELEMENT":           web.wait_for_element,
            "PAUSE":                      web.pause,
            "RUN_SCRIPT":                 web.run_script,
        }

    def _build_locator(
        self, locator_type: str, locator_value: str
    ):
        mapping = {
            "ID":                By.ID,
            "XPATH":             By.XPATH,
            "CSS_SELECTOR":      By.CSS_SELECTOR,
            "NAME":              By.NAME,
            "CLASS_NAME":        By.CLASS_NAME,
            "TAG_NAME":          By.TAG_NAME,
            "LINK_TEXT":         By.LINK_TEXT,
            "PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT,
        }

        import re
        key = locator_type.strip().upper()
        val = locator_value.strip()

        if key not in mapping:
            raise ValueError(
                f"Unsupported locator type: '{locator_type}'"
            )

        if not val:
            raise ValueError(
                f"Empty locator value for type '{locator_type}'"
            )

        # Reject dynamic react-select IDs — change every page load
        if key == "ID" and re.search(r'react-select-\d+-', val, re.IGNORECASE):
            raise ValueError(
                f"Dynamic react-select ID '{val}' changes every page load. "
                "Use SELECT_OPTION action with the visible option text instead."
            )

        # Reject bare tag selectors — matches everything on the page
        if key == "CSS_SELECTOR" and val.lower().strip() in {
            'div', 'span', 'a', 'button', 'input', 'ul', 'li'
        }:
            raise ValueError(
                f"CSS selector '{val}' is too broad. "
                "Use a more specific selector."
            )

        return (mapping[key], val)


    def execute(self, step: dict):
        """Dispatch one normalised module-CSV row."""

        action_name = step.get(MOD_ACTION, "").strip().upper()

        if not action_name:
            logger.warning("Blank action – skipped")
            return

        if action_name not in self.registry:
            logger.warning(f"Unknown action skipped: {action_name}")
            return

        fn   = self.registry[action_name]
        data = step.get(MOD_TEST_DATA) or None

        logger.info(
            f"  [{action_name}] "
            f"{step.get(MOD_DESCRIPTION, '')}"
            + (f" | data={data}" if data else "")
        )

        if action_name in self.NO_ARGS:
            return fn()

        if action_name in self.NO_LOCATOR:
            return fn(data) if data else fn()

        # ----------------------------------------------------------
        # Locator resolution — layered strategy
        # ----------------------------------------------------------
        loc_type = step.get(MOD_LOCATOR_TYPE, "").strip()
        loc_val  = step.get(MOD_LOCATOR_VAL,  "").strip()

        description = step.get(MOD_DESCRIPTION, "").strip()

        if loc_type and loc_val:
            # CSV supplies explicit locator — try it first
            locator = self._build_locator(loc_type, loc_val)
            logger.info(
                f"  [Locator] using CSV locator: {loc_type}={loc_val}"
            )

            # If smart locator is also on, verify the CSV locator actually
            # finds the element. If it finds 0 elements fall back to smart
            # locator — this handles old/broken CSVs automatically.
            if self.config.smart_locator:
                try:
                    found = self.web.driver.find_elements(
                        locator[0], locator[1]
                    )
                    if not found:
                        logger.warning(
                            f"  [Locator] CSV locator matched 0 elements "
                            f"— falling back to SmartLocator"
                        )
                        locator = self.resolver.resolve(description)
                except Exception:
                    logger.warning(
                        f"  [Locator] CSV locator invalid "
                        f"— falling back to SmartLocator"
                    )
                    locator = self.resolver.resolve(description)

        elif self.config.smart_locator:
            # No locator in CSV — resolve by description automatically
            if not description:
                raise ValueError(
                    "Basic Sanity column is empty — smart locator needs "
                    "a description to find the element. "
                    "Add a description like 'Enter email address' or "
                    "add Locator + Locator Value to the CSV row."
                )
            locator = self.resolver.resolve(description)

        else:
            raise ValueError(
                f"No locator provided for step '{description}' and "
                "smart_locator is disabled. "
                "Add Locator + Locator Value columns to the CSV row."
            )

        return fn(locator, data) if data else fn(locator)


# =========================================================
# TEST RUNNER
# =========================================================

class TestRunner:

    def __init__(self, config: FrameworkConfig):

        self.config  = config
        self.driver  = DriverFactory.create_driver(config)
        self.context = FrameworkContext()

        web = WebActions(self.driver, self.context, config)

        self.engine = ActionEngine(web, config)

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _now(self) -> str:
        return datetime.datetime.now().strftime(
            "Executed@%I_%M%p%B%d"
        )

    def _should_run(self, value) -> bool:
        return str(value).strip().upper() in {
            "Y", "YES", "TRUE", "1"
        }

    def _is_comment(self, step: dict) -> bool:
        return step.get(MOD_DESCRIPTION, "").strip().startswith("#")

    # ----------------------------------------------------------
    # Module-level results written back to ExecutionSequence.csv
    # ----------------------------------------------------------

    def _update_suite_row(
        self,
        row:          dict,
        failed_count: int,
        status:       str
    ):
        row[ES_LAST_EXEC]    = self._now()
        row[ES_FAILED_COUNT] = str(failed_count)
        row[ES_STATUS]       = status

    # ----------------------------------------------------------
    # Step-level result written back to module CSV + step log
    # ----------------------------------------------------------

    def _update_step(self, step: dict, status: str, module_name: str = ""):

        if status == "PASS":
            step[MOD_EXECUTED_ON] = self._now()             # timestamp = passed
        elif status == "FAIL":
            step[MOD_EXECUTED_ON] = f"FAIL@{self._now()}"  # FAIL + timestamp
        else:
            step[MOD_EXECUTED_ON] = "SKIPPED"

        description = step.get(MOD_DESCRIPTION, "").strip() or "(no description)"
        step_logger.info(
            f"{module_name} | {description} | {status}"
        )

    # ----------------------------------------------------------
    # Main execution loop
    # ----------------------------------------------------------

    def run(self):

        suite_rows, suite_headers = CsvUtil.read_csv(
            self.config.execution_file
        )

        # Filter out completely empty rows — can appear at end of CSV
        suite_rows = [
            r for r in suite_rows
            if any(v for v in r.values() if v)
        ]

        logger.info(
            f"ExecutionSequence loaded: {len(suite_rows)} entries"
        )

        try:

            for suite_row in suite_rows:

                module_name = suite_row.get(ES_MODULE_NAME, "").strip()
                run_flag    = suite_row.get(ES_RUN, "")
                test_url    = suite_row.get(ES_TEST_URL, "").strip()

                if not self._should_run(run_flag):
                    logger.info(f"Skipping module: {module_name}")
                    continue

                logger.info(
                    f"{'='*55}\n"
                    f"  Module : {module_name}\n"
                    f"  URL    : {test_url}\n"
                    f"{'='*55}"
                )

                module_csv = os.path.join(
                    self.config.module_base_path,
                    f"{module_name}.csv"
                )

                if not os.path.exists(module_csv):
                    logger.error(
                        f"Module CSV not found: {module_csv}"
                    )
                    self._update_suite_row(
                        suite_row, 0, "CSV NOT FOUND"
                    )
                    continue

                test_steps, mod_headers = CsvUtil.read_csv(
                    module_csv
                )

                logger.info(
                    f"Steps loaded: {len(test_steps)}"
                )

                # Navigate to the module's URL before running steps.
                if test_url:
                    self.engine.web.open_url(test_url)

                failed_count = 0
                status       = "ALL PASS"

                try:
                    failed_count = self._run_module(test_steps, module_name)

                    status = "FAILED" if failed_count else "ALL PASS"

                except Exception as e:
                    # Only raised when continue_on_failure=False.
                    failed_count += 1
                    status = "FAILED"
                    logger.error(
                        f"Module aborted: {module_name} | {e}"
                    )

                finally:
                    # Always write step results back using original headers.
                    CsvUtil.write_csv(
                        module_csv,
                        test_steps,
                        original_fieldnames=mod_headers
                    )
                    # Update suite row results.
                    self._update_suite_row(
                        suite_row, failed_count, status
                    )

                logger.info(
                    f"Module done: {module_name} | "
                    f"Status={status} | Failed={failed_count}"
                )

            logger.info("All modules completed.")

        except Exception as e:
            logger.error(f"Framework error: {e}")

        finally:
            # Write results back to ExecutionSequence.csv using
            # original headers captured when it was first read.
            CsvUtil.write_csv(
                self.config.execution_file,
                suite_rows,
                original_fieldnames=suite_headers
            )

            self.driver.quit()

            logger.info(
                f"Session ended | "
                f"Total exceptions: {self.context.exception_count}"
            )

    def _run_module(self, test_steps: list, module_name: str = "") -> int:
        """
        Executes all steps in a module CSV.
        Returns the number of failed steps.
        """
        failed = 0

        step_logger.info(
            f"{'=' * 55}"
        )
        step_logger.info(
            f"MODULE: {module_name}"
        )
        step_logger.info(
            f"{'=' * 55}"
        )

        for step in test_steps:

            if self._is_comment(step):
                logger.info(
                    f"# {step.get(MOD_DESCRIPTION, '')}"
                )
                continue

            if not self._should_run(step.get(MOD_RUN, "")):
                self._update_step(step, "SKIPPED", module_name)
                continue

            try:
                # Wait for page to fully load before each step
                if self.config.wait_for_page_load:
                    self.engine.web._wait_for_page_load()

                # Wait for any overlay/spinner to clear before clicking
                # Prevents "element click intercepted" errors
                self.engine.web._wait_for_overlay()

                # Per-step delay — check Extra Data column first.
                # If Extra Data contains a number, use it as the delay
                # for this step (overrides the global step_delay).
                # e.g. Extra Data = 3  → wait 3 seconds before this step
                #      Extra Data = 0  → no wait for this step
                #      Extra Data = "" → use global step_delay (default)
                extra = step.get(MOD_EXTRA, "").strip()
                try:
                    step_wait = float(extra) if extra else self.config.step_delay
                except ValueError:
                    step_wait = self.config.step_delay

                if step_wait > 0:
                    logger.info(
                        f"  [delay] waiting {step_wait}s before step"
                    ) if step_wait != self.config.step_delay else None
                    time.sleep(step_wait)

                self.engine.execute(step)
                self._update_step(step, "PASS", module_name)

            except Exception as e:
                failed += 1
                self._update_step(step, "FAIL", module_name)

                # Log the full exception so failures are never silent
                logger.error(
                    f"STEP FAILED: {step.get(MOD_DESCRIPTION, '')} | "
                    f"{type(e).__name__}: {e}"
                )

                if not self.config.continue_on_failure:
                    raise

        return failed


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    try:
        config = FrameworkConfig()
        runner = TestRunner(config)
        runner.run()

    except Exception as e:
        logger.exception(f"Framework startup failed: {e}")
