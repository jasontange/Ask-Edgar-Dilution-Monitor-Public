"""
DAS Trader Montage Monitor + Ask Edgar Dilution Overlay
-------------------------------------------------------
Monitors the active DAS Trader montage window for ticker changes,
fetches dilution risk data from the Ask Edgar API, and displays
results in an always-on-top overlay panel.
"""

import os
import threading
import time
import webbrowser
import requests
import tkinter as tk
import win32gui
import re

# Load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ──────────────────────────────────────────────────────────────────
# API keys – set these as environment variables or in a .env file
# See .env.example for details
ASKEDGAR_DILUTION_KEY = os.environ.get("ASKEDGAR_DILUTION_API_KEY", "")
ASKEDGAR_DATA_KEY = os.environ.get("ASKEDGAR_DATA_API_KEY", "")
MASSIVE_KEY = os.environ.get("MASSIVE_API_KEY", "")

if not ASKEDGAR_DILUTION_KEY or not ASKEDGAR_DATA_KEY:
    print("ERROR: Missing API keys. Copy .env.example to .env and fill in your keys.")
    print("  ASKEDGAR_DILUTION_API_KEY - from askedgar.io enterprise plan")
    print("  ASKEDGAR_DATA_API_KEY     - from askedgar.io enterprise plan")
    print("  MASSIVE_API_KEY           - from massive.com (optional, for live price)")

DILUTION_API_URL = "https://eapi.askedgar.io/enterprise/v1/dilution-rating"
DILUTION_API_KEY = ASKEDGAR_DILUTION_KEY
FLOAT_API_URL = "https://eapi.askedgar.io/enterprise/v1/float-outstanding"
FLOAT_API_KEY = ASKEDGAR_DATA_KEY
NEWS_API_URL = "https://eapi.askedgar.io/enterprise/v1/news"
NEWS_API_KEY = ASKEDGAR_DATA_KEY
DILDATA_API_URL = "https://eapi.askedgar.io/enterprise/v1/dilution-data"
DILDATA_API_KEY = ASKEDGAR_DATA_KEY
PRICE_API_URL = "https://api.massive.com/v2/last/trade"
PRICE_API_KEY = MASSIVE_KEY
POLL_INTERVAL = 1.5

# Colors (dark theme matching React design)
BG = "#111315"
BG_CARD = "#17191c"
BG_ROW = "#222529"
BORDER = "#2a2d31"
BORDER_INNER = "#2d3136"
FG = "#E0E0E0"
FG_DIM = "#9aa0a6"
FG_INFO = "#c7c9cc"
ACCENT = "#00D4FF"

RISK_BG = {
    "High": "#C62828",
    "Medium": "#E65100",
    "Low": "#2E7D32",
    "N/A": "#555555",
}


def risk_bg(level: str) -> str:
    return RISK_BG.get(level, "#555555")


def fmt_millions(val) -> str:
    if val is None:
        return "N/A"
    m = val / 1_000_000
    if m >= 1:
        return f"{m:.2f}M"
    return f"{val / 1000:.0f}K"


# ── Window Monitor ──────────────────────────────────────────────────────────
def find_montage_windows() -> dict[int, str]:
    """Return {hwnd: ticker} for all visible DAS montage windows."""
    windows = {}

    def enum_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if re.match(r'^[A-Z]{1,5}\s+\d', title):
            windows[hwnd] = title.split()[0]

    win32gui.EnumWindows(enum_callback, None)
    return windows


def find_tos_tickers() -> dict[int, list[str]]:
    """Return {hwnd: [tickers]} for thinkorswim chart windows."""
    windows = {}

    def enum_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        # "PRSO, MOBX, TURB - Charts - 61612650SCHW Main@thinkorswim [build 1990]"
        if "thinkorswim" in title and " - Charts - " in title:
            ticker_part = title.split(" - Charts - ")[0]
            tickers = [t.strip() for t in ticker_part.split(",") if t.strip()]
            if tickers:
                windows[hwnd] = tickers

    win32gui.EnumWindows(enum_callback, None)
    return windows


# ── Ask Edgar APIs ──────────────────────────────────────────────────────────
def fetch_dilution_data(ticker: str) -> dict | None:
    try:
        resp = requests.get(
            DILUTION_API_URL,
            headers={"API-KEY": DILUTION_API_KEY, "Content-Type": "application/json"},
            params={"ticker": ticker, "offset": 0, "limit": 10},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success" and data.get("results"):
            return data["results"][0]
    except Exception as e:
        print(f"Dilution API error for {ticker}: {e}")
    return None


def fetch_float_data(ticker: str) -> dict | None:
    try:
        resp = requests.get(
            FLOAT_API_URL,
            headers={"API-KEY": FLOAT_API_KEY, "Content-Type": "application/json"},
            params={"ticker": ticker, "offset": 0, "limit": 100},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success" and data.get("results"):
            return data["results"][0]
    except Exception as e:
        print(f"Float API error for {ticker}: {e}")
    return None


def fetch_news_and_grok(ticker: str) -> tuple[list[dict], str | None, str | None, str | None, list[dict]]:
    """Fetch recent news/8-K/6-K (top 2), latest grok, and all jmt415 notes."""
    headlines = []
    grok_line = None
    grok_date = None
    grok_url = None
    jmt415_notes = []
    try:
        resp = requests.get(
            NEWS_API_URL,
            headers={"API-KEY": NEWS_API_KEY, "Content-Type": "application/json"},
            params={"ticker": ticker, "offset": 0, "limit": 100},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success":
            for r in data.get("results", []):
                ft = r.get("form_type")
                if ft in ("news", "8-K", "6-K") and len(headlines) < 2:
                    headlines.append(r)
                if ft == "grok" and grok_line is None:
                    summary = r.get("summary", "")
                    for line in summary.split("\n"):
                        line = line.strip().lstrip("-").strip()
                        if line:
                            grok_line = line
                            break
                    # created_at includes time, fall back to filed_at
                    grok_date = r.get("created_at") or r.get("filed_at", "")
                    grok_url = r.get("url") or r.get("document_url")
                if ft == "jmt415" and len(jmt415_notes) < 3:
                    jmt415_notes.append(r)
    except Exception as e:
        print(f"News API error for {ticker}: {e}")
    return headlines, grok_line, grok_date, grok_url, jmt415_notes


def fetch_last_price(ticker: str) -> float | None:
    try:
        resp = requests.get(
            f"{PRICE_API_URL}/{ticker}",
            params={"apiKey": PRICE_API_KEY},
            timeout=10,
        )
        data = resp.json()
        results = data.get("results", data)
        return results.get("p")
    except Exception as e:
        print(f"Price API error for {ticker}: {e}")
    return None


def fetch_in_play_dilution(ticker: str) -> tuple[list[dict], list[dict], float]:
    """Fetch dilution-data and split into in-play warrants and convertibles.
    Returns (warrants, convertibles, stock_price) filtered by price proximity and registration."""
    price = fetch_last_price(ticker)
    if price is None or price <= 0:
        return [], [], 0.0

    max_price = price * 4

    try:
        resp = requests.get(
            DILDATA_API_URL,
            headers={"API-KEY": DILDATA_API_KEY, "Content-Type": "application/json"},
            params={"ticker": ticker, "offset": 0, "limit": 40},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") != "success":
            return [], [], price
    except Exception as e:
        print(f"Dilution-data API error for {ticker}: {e}")
        return [], [], price

    warrants = []
    convertibles = []

    for item in data.get("results", []):
        registered = item.get("registered", "")
        if "Not Registered" in registered:
            continue

        details_lower = (item.get("details") or "").lower()
        is_warrant = "warrant" in details_lower or "option" in details_lower

        if is_warrant and item.get("warrants_exercise_price"):
            if item["warrants_exercise_price"] <= max_price:
                remaining = item.get("warrants_remaining", 0) or 0
                if remaining > 0:
                    warrants.append(item)
        elif not is_warrant and item.get("conversion_price"):
            if item["conversion_price"] <= max_price:
                remaining = item.get("underlying_shares_remaining", 0) or 0
                if remaining > 0:
                    convertibles.append(item)

    return warrants, convertibles, price


def extract_headline(item: dict) -> str:
    if item.get("title"):
        return item["title"]
    summary = item.get("summary", "")
    if summary.startswith("HEADLINE:"):
        return summary.split("HEADLINE:")[1].split("\n")[0].strip()
    return f"{item.get('form_type', '')} Filing"


# ── Overlay UI ──────────────────────────────────────────────────────────────
class DilutionOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ask Edgar - Dilution Monitor")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.geometry("480x620+50+50")
        self.root.minsize(400, 300)

        self._drag_data = {"x": 0, "y": 0}
        self.current_ticker = None
        self._known_windows: dict[int, str] = {}  # DAS: hwnd -> ticker
        self._known_tos: dict[int, list[str]] = {}  # ToS: hwnd -> [tickers]
        self._build_ui()
        self._start_monitor()

    def _build_ui(self):
        # ── Header card (draggable) ──
        header_card = tk.Frame(self.root, bg=BG_CARD,
                               highlightbackground=BORDER, highlightthickness=1)
        header_card.pack(fill="x", padx=8, pady=(8, 0))
        header_card.bind("<Button-1>", self._start_drag)
        header_card.bind("<B1-Motion>", self._on_drag)

        header_inner = tk.Frame(header_card, bg=BG_CARD, padx=12, pady=10)
        header_inner.pack(fill="x")
        header_inner.bind("<Button-1>", self._start_drag)
        header_inner.bind("<B1-Motion>", self._on_drag)

        self.ticker_label = tk.Label(
            header_inner, text="Waiting...", fg=ACCENT,
            bg=BG_CARD, font=("Consolas", 24, "bold"),
        )
        self.ticker_label.pack(side="left")

        self.overall_badge = tk.Label(
            header_inner, text="", fg="white", bg="#555555",
            font=("Consolas", 12, "bold"), padx=10, pady=4,
        )
        self.overall_badge.pack(side="right")

        self.info_label = tk.Label(
            header_card, text="", fg=FG_INFO, bg=BG_CARD,
            font=("Consolas", 10), anchor="w",
        )
        self.info_label.pack(fill="x", padx=14, pady=(0, 10))

        # ── Scrollable content ──
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=0, pady=0)

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.content_frame = tk.Frame(canvas, bg=BG)

        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._canvas_window = canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_resize(event):
            canvas.itemconfig(self._canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas = canvas

        self._show_waiting()

    # ── Display states ──────────────────────────────────────────────────────
    def _clear(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_waiting(self):
        self._clear()
        tk.Label(
            self.content_frame,
            text="Load a ticker in DAS or thinkorswim\nto see dilution data here.",
            fg="#555555", bg=BG, font=("Consolas", 12), justify="center",
        ).pack(pady=60)

    def _show_loading(self, ticker: str):
        self._clear()
        self.ticker_label.config(text=ticker)
        self.overall_badge.config(text="...", bg="#555555")
        self.info_label.config(text="Loading...")
        tk.Label(
            self.content_frame,
            text=f"Fetching data for {ticker}...",
            fg=ACCENT, bg=BG, font=("Consolas", 12),
        ).pack(pady=60)
        self.root.update_idletasks()

    def _show_no_data(self, ticker: str):
        self._clear()
        self.overall_badge.config(text="NO DATA", bg="#555555")
        self.info_label.config(text="")
        tk.Label(
            self.content_frame,
            text=f"No dilution data available for {ticker}.",
            fg="#FF6666", bg=BG, font=("Consolas", 11), justify="center",
        ).pack(pady=60)

    def _make_card(self, parent, title: str = None) -> tk.Frame:
        """Create a bordered card frame, optionally with a section header."""
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=8, pady=(6, 0))
        if title:
            hdr = tk.Label(card, text=title, fg=ACCENT, bg=BG_CARD,
                           font=("Consolas", 14, "bold"), anchor="w", padx=12, pady=8)
            hdr.pack(fill="x")
            tk.Frame(card, bg=BORDER, height=1).pack(fill="x")
        return card

    def _show_data(self, ticker: str, dilution: dict, floatdata: dict | None,
                   news: list[dict] | None = None, grok_line: str | None = None,
                   grok_date: str | None = None, grok_url: str | None = None,
                   in_play_warrants: list[dict] | None = None,
                   in_play_converts: list[dict] | None = None,
                   stock_price: float = 0.0,
                   jmt415_notes: list[dict] | None = None):
        self._clear()

        risk = dilution.get("overall_offering_risk", "N/A")
        self.overall_badge.config(text=f"RISK: {risk}", bg=risk_bg(risk))

        # ── Info line from float data ──
        if floatdata:
            flt = fmt_millions(floatdata.get("float"))
            outs = fmt_millions(floatdata.get("outstanding"))
            mc = fmt_millions(floatdata.get("market_cap_final"))
            sector = floatdata.get("sector", "")
            country = floatdata.get("country", "")
            self.info_label.config(
                text=f"Float/OS: {flt}/{outs}  |  MC: {mc}  |  {sector}  |  {country}"
            )
        else:
            self.info_label.config(text="")

        # ── Feed card (news + grok) ──
        has_feed = news or grok_line
        if has_feed:
            feed_card = self._make_card(self.content_frame)
            feed_inner = tk.Frame(feed_card, bg=BG_CARD, padx=8, pady=8)
            feed_inner.pack(fill="x")

            if news:
                for item in news:
                    headline = extract_headline(item)
                    url = item.get("url") or item.get("document_url")
                    form = item.get("form_type", "")
                    raw_date = item.get("created_at") or item.get("filed_at", "")
                    date = raw_date[:16].replace("T", " ")
                    self._add_feed_item(feed_inner, form, headline, url, date)

            if grok_line:
                grok_date_str = ""
                if grok_date:
                    grok_date_str = grok_date[:16].replace("T", " ")
                self._add_feed_item(feed_inner, "grok", grok_line, grok_url, grok_date_str)

        # ── Risk badges card ──
        dilution_url = f"https://app.askedgar.io/ticker/{ticker}/dilution"
        badges_card = self._make_card(self.content_frame)
        badges_inner = tk.Frame(badges_card, bg=BG_CARD, padx=8, pady=8, cursor="hand2")
        badges_inner.pack(fill="x")
        badges_inner.bind("<Button-1>", lambda e, u=dilution_url: webbrowser.open(u))

        badge_items = [
            ("Overall Risk", risk),
            ("Offering", dilution.get("offering_ability", "N/A")),
            ("Dilution", dilution.get("dilution", "N/A")),
            ("Frequency", dilution.get("offering_frequency", "N/A")),
            ("Cash Need", dilution.get("cash_need", "N/A")),
            ("Warrants", dilution.get("warrant_exercise", "N/A")),
        ]
        for label, level in badge_items:
            self._add_badge(badges_inner, label, level, dilution_url)

        # ── Offering Ability card ──
        offering_desc = dilution.get("offering_ability_desc")
        if offering_desc:
            self._add_offering_ability_card(offering_desc)

        # ── In Play Dilution card ──
        if in_play_warrants or in_play_converts:
            self._add_in_play_section(in_play_warrants or [], in_play_converts or [], stock_price)

        # ── JMT415 Previous Notes card ──
        if jmt415_notes:
            self._add_jmt415_card(jmt415_notes)

        # ── Management Commentary card ──
        commentary = dilution.get("mgmt_commentary")
        if commentary:
            self._add_section_card("Mgmt Commentary", commentary)

    def _add_badge(self, parent, label: str, level: str, url: str | None = None):
        frame = tk.Frame(parent, bg=BG_CARD, padx=4, pady=2, cursor="hand2")
        frame.pack(side="left", padx=4)

        lbl = tk.Label(
            frame, text=label, fg=FG_DIM, bg=BG_CARD,
            font=("Consolas", 9), cursor="hand2",
        )
        lbl.pack()

        badge = tk.Label(
            frame, text=f" {level} ", fg="white", bg=risk_bg(level),
            font=("Consolas", 10, "bold"), padx=6, pady=2, cursor="hand2",
        )
        badge.pack()

        if url:
            for w in (frame, lbl, badge):
                w.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

    def _add_feed_item(self, parent, form_type: str, headline: str,
                       url: str | None, date: str = ""):
        """Feed row with source stripe on the left. Entire row is clickable."""
        SOURCE_COLORS = {
            "news": ACCENT,
            "8-K": "#E65100",
            "6-K": "#E65100",
            "grok": "#9C27B0",
        }
        source_color = SOURCE_COLORS.get(form_type, "#555555")
        tag = form_type.upper() if form_type != "news" else "NEWS"

        # Truncate grok output to ~240 chars
        if form_type == "grok" and len(headline) > 240:
            headline = headline[:237] + "..."

        row = tk.Frame(parent, bg=BG_ROW,
                       highlightbackground=BORDER_INNER, highlightthickness=1)
        row.pack(fill="x", pady=2)

        # Source stripe (left column)
        stripe = tk.Label(
            row, text=tag, fg="white", bg=source_color,
            font=("Consolas", 9, "bold"), width=6, padx=6, pady=8,
        )
        stripe.pack(side="left", fill="y")

        # Content area
        content = tk.Frame(row, bg=BG_ROW, padx=8, pady=4)
        content.pack(side="left", fill="both", expand=True)

        top_row = tk.Frame(content, bg=BG_ROW)
        top_row.pack(fill="x")

        if date:
            tk.Label(
                top_row, text=date, fg=FG_DIM, bg=BG_ROW,
                font=("Consolas", 9),
            ).pack(side="left", padx=(0, 8))

        hl_label = tk.Label(
            top_row, text=headline, fg="white", bg=BG_ROW,
            font=("Consolas", 9, "bold"), anchor="w", wraplength=350,
            justify="left",
        )
        hl_label.pack(side="left", fill="x", expand=True)

        def _rewrap_hl(event, lbl=hl_label):
            lbl.config(wraplength=max(event.width - 120, 100))
        row.bind("<Configure>", _rewrap_hl)

        # Make entire row clickable if there's a URL
        if url:
            row.config(cursor="hand2")
            def _bind_click(widget, target_url):
                widget.bind("<Button-1>", lambda e, u=target_url: webbrowser.open(u))
                widget.config(cursor="hand2")
            for w in (row, stripe, content, top_row, hl_label):
                _bind_click(w, url)
            # Also bind date label if it exists
            for child in top_row.winfo_children():
                _bind_click(child, url)

    def _add_section_card(self, title: str, text: str):
        """Section card with header + bottom border + wrapped text content."""
        card = self._make_card(self.content_frame, title=title)
        body = tk.Frame(card, bg=BG_CARD, padx=14, pady=12)
        body.pack(fill="x")
        text_label = tk.Label(
            body, text=text, fg=FG, bg=BG_CARD,
            font=("Consolas", 10), justify="left", anchor="w",
        )
        text_label.pack(fill="x")
        def _rewrap(event, lbl=text_label):
            lbl.config(wraplength=max(event.width - 4, 100))
        body.bind("<Configure>", _rewrap)

    def _add_offering_ability_card(self, desc: str):
        """Offering Ability card with color-coded capacity values."""
        card = self._make_card(self.content_frame, title="Offering Ability")
        body = tk.Frame(card, bg=BG_CARD, padx=14, pady=12)
        body.pack(fill="x")

        # Parse and color individual segments — stacked vertically
        parts = [p.strip() for p in desc.split(",")]

        for part in parts:
            part_lower = part.lower()
            if "pending s-1" in part_lower or "pending f-1" in part_lower:
                color = "#FF4444"
                bold = True
            elif ("shelf capacity" in part_lower or "atm capacity" in part_lower):
                if "$0.00" in part:
                    color = "#FF4444"
                    bold = False
                else:
                    color = "#4CAF50"
                    bold = True
            else:
                color = FG
                bold = False

            font = ("Consolas", 10, "bold") if bold else ("Consolas", 10)
            tk.Label(
                body, text=part, fg=color, bg=BG_CARD,
                font=font, anchor="w",
            ).pack(fill="x")

    def _add_jmt415_card(self, notes: list[dict]):
        """JMT415 Previous Notes card with bulleted list."""
        card = self._make_card(self.content_frame, title="JMT415 Previous Notes")
        body = tk.Frame(card, bg=BG_CARD, padx=14, pady=8)
        body.pack(fill="x")

        for note in notes:
            date = (note.get("filed_at") or "")[:10]
            summary = note.get("summary", "").strip()
            # Take first meaningful line
            text = ""
            for line in summary.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line:
                    text = line
                    break
            if not text:
                text = note.get("title") or "Note"

            row = tk.Frame(body, bg=BG_CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"\u2022  {date}", fg=FG_DIM, bg=BG_CARD,
                     font=("Consolas", 9)).pack(side="left", padx=(0, 8))
            note_label = tk.Label(row, text=text, fg=FG, bg=BG_CARD,
                                  font=("Consolas", 9), anchor="w",
                                  wraplength=350, justify="left")
            note_label.pack(side="left", fill="x", expand=True)

            def _rewrap(event, lbl=note_label):
                lbl.config(wraplength=max(event.width - 140, 100))
            row.bind("<Configure>", _rewrap)

    def _add_in_play_section(self, warrants: list[dict], convertibles: list[dict],
                             stock_price: float = 0.0):
        card = self._make_card(self.content_frame, title="In Play Dilution")
        body = tk.Frame(card, bg=BG_CARD, padx=14, pady=8)
        body.pack(fill="x")

        if warrants:
            tk.Label(
                body, text="WARRANTS", fg="#FFD600", bg=BG_CARD,
                font=("Consolas", 11, "bold"), anchor="w",
            ).pack(fill="x", pady=(4, 4))
            for w in warrants:
                ex_price = w.get("warrants_exercise_price", 0) or 0
                above = ex_price >= stock_price > 0
                self._add_dilution_row(
                    body, w.get("details", ""),
                    f"Remaining: {fmt_millions(w.get('warrants_remaining'))}",
                    f"Strike: ${ex_price:.2f}",
                    (w.get("filed_at") or "")[:10],
                    w.get("askedgar_url"),
                    above,
                )

        if convertibles:
            tk.Label(
                body, text="CONVERTIBLES", fg="#FFD600", bg=BG_CARD,
                font=("Consolas", 11, "bold"), anchor="w",
            ).pack(fill="x", pady=(8, 4))
            for c in convertibles:
                conv_price = c.get("conversion_price", 0) or 0
                above = conv_price >= stock_price > 0
                self._add_dilution_row(
                    body, c.get("details", ""),
                    f"Shares: {fmt_millions(c.get('underlying_shares_remaining'))}",
                    f"Conv: ${conv_price:.2f}",
                    (c.get("filed_at") or "")[:10],
                    c.get("askedgar_url"),
                    above,
                )

    def _add_dilution_row(self, parent, details, remaining, price, filed,
                          url=None, price_above=False):
        # Green if price >= stock price, orange if below
        highlight = "#4CAF50" if price_above else "#FF9800"

        row = tk.Frame(parent, bg=BG_ROW,
                       highlightbackground=BORDER_INNER, highlightthickness=1)
        row.pack(fill="x", pady=2)

        inner = tk.Frame(row, bg=BG_ROW, padx=10, pady=4)
        inner.pack(fill="x")

        # Line 1: details (truncated if long)
        detail_text = details if len(details) <= 60 else details[:57] + "..."
        tk.Label(inner, text=detail_text, fg="white", bg=BG_ROW,
                 font=("Consolas", 9), anchor="w").pack(fill="x")

        # Line 2: remaining | price | filed
        data_row = tk.Frame(inner, bg=BG_ROW)
        data_row.pack(fill="x", pady=(2, 0))
        tk.Label(data_row, text=remaining, fg=highlight, bg=BG_ROW,
                 font=("Consolas", 9, "bold")).pack(side="left")
        tk.Label(data_row, text="  |  ", fg=FG_DIM, bg=BG_ROW,
                 font=("Consolas", 9)).pack(side="left")
        tk.Label(data_row, text=price, fg=highlight, bg=BG_ROW,
                 font=("Consolas", 9, "bold")).pack(side="left")
        tk.Label(data_row, text=f"  |  Filed: {filed}", fg=FG_DIM, bg=BG_ROW,
                 font=("Consolas", 9)).pack(side="left")

        if url:
            row.config(cursor="hand2")
            def _bind_click(widget, target_url):
                widget.bind("<Button-1>", lambda e, u=target_url: webbrowser.open(u))
            for child in (row, inner, data_row, *inner.winfo_children(), *data_row.winfo_children()):
                _bind_click(child, url)

    # ── Dragging ──
    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # ── Monitor thread ──
    def _start_monitor(self):
        def poll():
            while True:
                changed_ticker = None

                # ── DAS montage windows ──
                current = find_montage_windows()  # {hwnd: ticker}
                for hwnd, ticker in current.items():
                    old_ticker = self._known_windows.get(hwnd)
                    if old_ticker is not None and ticker != old_ticker:
                        changed_ticker = ticker
                        break
                if changed_ticker is None:
                    new_hwnds = set(current) - set(self._known_windows)
                    for hwnd in new_hwnds:
                        ticker = current[hwnd]
                        if ticker != self.current_ticker:
                            changed_ticker = ticker
                            break
                self._known_windows = current

                # ── thinkorswim chart windows ──
                if changed_ticker is None:
                    tos_current = find_tos_tickers()  # {hwnd: [tickers]}
                    for hwnd, tickers in tos_current.items():
                        old_tickers = self._known_tos.get(hwnd, [])
                        new_syms = [t for t in tickers if t not in old_tickers]
                        if new_syms:
                            changed_ticker = new_syms[0]
                            break
                    if changed_ticker is None:
                        new_hwnds = set(tos_current) - set(self._known_tos)
                        for hwnd in new_hwnds:
                            for t in tos_current[hwnd]:
                                if t != self.current_ticker:
                                    changed_ticker = t
                                    break
                            if changed_ticker:
                                break
                    self._known_tos = tos_current

                if changed_ticker and changed_ticker != self.current_ticker:
                    self.current_ticker = changed_ticker
                    self.root.after(0, self._on_ticker_change, changed_ticker)
                time.sleep(POLL_INTERVAL)

        threading.Thread(target=poll, daemon=True).start()

    def _on_ticker_change(self, ticker: str):
        self._show_loading(ticker)

        def fetch():
            dilution = fetch_dilution_data(ticker)
            floatdata = fetch_float_data(ticker)
            news, grok_line, grok_date, grok_url, jmt415_notes = fetch_news_and_grok(ticker)
            warrants, converts, stock_price = fetch_in_play_dilution(ticker)
            if dilution:
                self.root.after(0, self._show_data, ticker, dilution, floatdata,
                                news, grok_line, grok_date, grok_url, warrants, converts, stock_price,
                                jmt415_notes)
            else:
                self.root.after(0, self._show_no_data, ticker)

        threading.Thread(target=fetch, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = DilutionOverlay()
    app.run()
