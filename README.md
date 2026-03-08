# Ask Edgar Dilution Monitor

A real-time desktop overlay that monitors your trading platform for ticker changes and instantly displays dilution risk data from [Ask Edgar](https://askedgar.io).

When you switch tickers in DAS Trader Pro or thinkorswim, the overlay automatically fetches and shows:

- **Dilution risk ratings** – Overall risk, offering ability, dilution level, frequency, cash need, warrants
- **Float & outstanding shares** – With market cap, sector, and country
- **Recent news & SEC filings** – 8-K, 6-K, and news headlines with clickable links
- **Grok AI summary** – Latest AI-generated analysis
- **Offering ability breakdown** – Shelf capacity, ATM capacity, pending S-1/F-1 registrations
- **In-play dilution** – Active warrants and convertibles near current price, color-coded by risk
- **JMT415 analyst notes** – Recent analyst commentary
- **Management commentary** – From Ask Edgar's dilution analysis

## What It Looks Like

The app runs as a dark-themed, always-on-top overlay panel. It sits alongside your trading platform and updates automatically as you click through tickers.

- Risk badges are color-coded: **red** (high), **orange** (medium), **green** (low)
- News items have colored stripes: **cyan** (news), **orange** (8-K/6-K), **purple** (grok)
- Warrants/convertibles highlight **green** if strike/conversion price is at or below current price (in the money), **orange** otherwise
- Pending S-1/F-1 registrations are bolded in red as a warning
- Everything is clickable – badges link to Ask Edgar, news links to source documents

## Compatibility

| Requirement | Details |
|---|---|
| **OS** | Windows only (uses `win32gui` for window detection) |
| **Python** | 3.10+ |
| **Trading Platforms** | DAS Trader Pro, thinkorswim (TD Ameritrade / Charles Schwab) |
| **API Access** | [Ask Edgar](https://askedgar.io) API trial key |

### How Platform Detection Works

- **DAS Trader Pro**: Monitors montage windows (`TICKER     0 -- 0     Company Name...`) and chart windows (`TICKER--5 Minute--`). Any ticker change in any montage or chart window triggers the overlay.
- **thinkorswim**: Monitors detached chart windows (`PRSO, MOBX, TURB - Charts - ...`). When a new ticker is entered in a chart tab, the overlay picks it up.

The app polls window titles every 1 second and detects when a ticker changes.

**ToS limitations**: Only *detached* chart windows are detected — charts embedded in the main ToS window (`Main@thinkorswim`) don't expose the active ticker in their window title. Switching between existing chart tabs also won't trigger a change since all tab tickers are always listed in the title. For best results with ToS, use detached chart windows and enter new tickers rather than clicking existing tabs.

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/jasontange/Ask-Edgar-Dilution-Monitor-Public.git
cd Ask-Edgar-Dilution-Monitor-Public
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

Edit `.env` with your API key:

```
ASKEDGAR_API_KEY=your_api_key_here
```

**Where to get your API key:**

- Request a free trial key at [askedgar.io](https://share-na2.hsforms.com/1mRWaNy8PRFuCZr5YJvjdQQqjkci). One key works for all endpoints.

### 4. Run it

```bash
python das_monitor.py
```

Open DAS Trader Pro or thinkorswim alongside the overlay. Click on a ticker and the data loads automatically.

## How to Customize

This is a single-file Python app (~770 lines). Some things you might want to change:

| What | Where | Notes |
|---|---|---|
| **Window size** | Line ~248 (`geometry("480x620+50+50")`) | Width x height + position |
| **Poll interval** | `POLL_INTERVAL = 1.0` | Seconds between window checks |
| **Colors** | Lines ~31-40 (color constants) | Dark theme hex values |
| **News limit** | `fetch_news_and_grok` params | Currently fetches top 2 news + 3 analyst notes |
| **Grok truncation** | `_add_feed_item` | Currently truncates at 240 chars |
| **Platform detection** | `find_montage_windows` / `find_tos_tickers` | Add regex patterns for other platforms |

### Adding Support for Other Platforms

To add a new trading platform, you need to:

1. Figure out how the platform formats its window titles (use a tool like Spy++ or just `print(win32gui.GetWindowText(hwnd))`)
2. Write a function similar to `find_montage_windows()` that extracts the ticker from the title
3. Add the detection logic to the `poll()` loop in `_start_monitor()`

## Tech Stack

- **Python 3.10+** with tkinter (built-in GUI)
- **win32gui** (pywin32) for Windows window enumeration
- **requests** for API calls
- **python-dotenv** for loading `.env` files

No frameworks, no build tools, no npm. Just one Python file.

## License

MIT – do whatever you want with it.
