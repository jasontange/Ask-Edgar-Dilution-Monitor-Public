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

## Quick Start (No coding experience needed)

### 1. Install Python

Download Python from [python.org/downloads](https://www.python.org/downloads/) and install it.

**IMPORTANT:** During installation, check the box that says **"Add Python to PATH"** — this is required.

### 2. Download this app

Click the green **"Code"** button at the top of this page, then click **"Download ZIP"**.

Extract the ZIP file to a folder on your computer (e.g. your Desktop).

### 3. Install the required packages

This app needs three Python packages to work. Open a **Command Prompt** (search "cmd" in the Windows Start menu), navigate to the folder you extracted, and run:

```bash
pip install requests pywin32 python-dotenv
```

Or if you prefer, install from the included requirements file:

```bash
pip install -r requirements.txt
```

> **What these packages do:**
> - `requests` – makes HTTP calls to the Ask Edgar API
> - `pywin32` – lets Python read your trading platform's window titles (Windows only)
> - `python-dotenv` – loads your API key from the `.env` file so you don't hardcode it

**Alternatively**, you can skip the command line and just **double-click `setup.bat`** — it installs the packages and creates your `.env` file automatically.

### 4. Add your API key

You need to create a file called `.env` in the app folder that holds your API key.

1. Find the file called **`.env.example`** in the app folder
2. **Make a copy** of it and rename the copy to **`.env`** (remove the `.example` part)
3. Open `.env` with Notepad and replace `your_api_key_here` with your actual API key:

```
ASKEDGAR_API_KEY=paste_your_key_here
```

> **Tip:** If you ran `setup.bat` in the previous step, the `.env` file was already created for you — just open it and paste your key.

**Don't have a key?** Request a free trial at [askedgar.io](https://share-na2.hsforms.com/1mRWaNy8PRFuCZr5YJvjdQQqjkci). One key works for all endpoints.

### 5. Launch the app

**Double-click `run.bat`** to start the overlay.

Open DAS Trader Pro or thinkorswim alongside it. Click on a ticker and the data loads automatically.

To stop the app, just close the overlay window (click the X) or close the command prompt window that opened with it.

---

<details>
<summary><b>Alternative: Setup via command line</b></summary>

```bash
git clone https://github.com/jasontange/Ask-Edgar-Dilution-Monitor-Public.git
cd Ask-Edgar-Dilution-Monitor-Public
pip install requests pywin32 python-dotenv
cp .env.example .env
# Edit .env with your API key
python das_monitor.py
```

</details>

## Important: Floating / Detached Windows Required

**This app can only detect tickers from floating (detached) windows.** It works by reading window titles, and only detached windows expose ticker information in their title.

### DAS Trader Pro

The monitor detects tickers from **floating (detached) montage and chart windows only**.

- **Montage windows** must be detached (floating) — the title looks like: `TICKER     0 -- 0     Company Name...`
- **Chart windows** must be detached (floating) — the title looks like: `TICKER--5 Minute--`
- **If your montages or charts are docked** inside the main DAS window, the app will NOT detect ticker changes

**How to detach a window in DAS:** Right-click the montage or chart tab and choose "Float" or drag it out of the main DAS layout.

### thinkorswim

The monitor detects tickers from **detached chart windows only**.

- **Detached chart windows** — the title looks like: `PRSO, MOBX, TURB - Charts - ...`
- **Charts inside the main window** (`Main@thinkorswim`) are NOT detected — the main window title doesn't expose the active ticker
- **Switching between existing chart tabs** won't trigger an update — all tab tickers are always listed in the title. For best results, **enter a new ticker** rather than clicking an existing tab

**How to detach a chart in ToS:** Right-click the chart tab and select "Detach" or drag it out of the main thinkorswim window.

### It's not detecting my ticker — now what?

If the overlay isn't picking up your ticker changes:

1. **Make sure your montage/chart windows are floating (detached)** — this is the #1 issue
2. The app polls window titles every 1 second — wait a moment after switching tickers
3. Make sure the app is actually running (you should see the overlay window and a command prompt)
4. Try entering a new ticker instead of clicking an existing tab (especially in ToS)

## Troubleshooting

If something isn't working, here's how to get help — whether you're debugging yourself or asking an AI assistant (Claude, Cursor, Copilot, etc.) to help you.

### Common issues

| Problem | Fix |
|---|---|
| `pip is not recognized` | Python isn't in your PATH. Reinstall Python and check **"Add Python to PATH"** |
| `ModuleNotFoundError: No module named 'requests'` | Packages aren't installed. Run: `pip install requests pywin32 python-dotenv` |
| `ModuleNotFoundError: No module named 'win32gui'` | Missing pywin32. Run: `pip install pywin32` |
| `ModuleNotFoundError: No module named 'dotenv'` | Missing python-dotenv. Run: `pip install python-dotenv` |
| `ERROR: Missing API key` | Open your `.env` file and add your API key. See Step 4 above |
| Overlay shows but no data loads | Check that your API key is correct and not expired |
| Overlay doesn't detect ticker changes | Your windows need to be **floating/detached**. See section above |

### Getting help from an AI assistant

If you're using an AI coding assistant (Claude Code, Cursor, Copilot, ChatGPT, etc.) to troubleshoot, **give it as much context as possible**. The more detail you provide, the faster it can help you.

**Include this information when asking for help:**

1. **Your trading platform setup:**
   - Which platform? (DAS Trader Pro, thinkorswim, or both)
   - Are your montages/charts **floating (detached)** or docked in the main window?
   - How many monitors are you using?
   - What does your desktop layout look like?

2. **Screenshots are extremely helpful:**
   - Screenshot of your full desktop showing your trading platform and the overlay
   - Screenshot of the specific montage/chart window you expect the app to read
   - Screenshot of the window's title bar (so the AI can see the exact format)
   - Screenshot of any error messages in the command prompt

3. **Error details:**
   - Copy-paste the full error message from the command prompt window
   - What did you expect to happen vs. what actually happened?

4. **Your setup:**
   - What version of Windows are you running?
   - Did you install Python fresh or was it already installed?
   - Did you run `setup.bat` or install packages manually?

> **Example prompt for your AI assistant:**
>
> *"The Ask Edgar overlay is running but not detecting my ticker. I'm using DAS Trader Pro with two monitors. My montages are docked in the main DAS window. Here's a screenshot of my setup: [paste screenshot]. Here's what the command prompt shows: [paste output]."*

This kind of detail lets the AI immediately spot the problem (in this example: the montages need to be detached/floating).

## How to Customize (Vibe Coding)

This is a single Python file — no frameworks, no build tools. You can customize it with an AI coding assistant like **Claude Code**, **Cursor**, or **GitHub Copilot** in VS Code.

### Setting up your editor

1. Install [VS Code](https://code.visualstudio.com/) or [Cursor](https://cursor.com/)
2. Open the extracted folder: **File > Open Folder** and select the app folder
3. You should see `das_monitor.py` in the file list on the left — that's the entire app

### Example: Change the window size

Try asking your AI assistant:

> "Make the overlay window wider — change it from 480px to 600px"

It will find this line in `das_monitor.py` and update it:

```python
# Before
self.root.geometry("480x620+50+50")

# After
self.root.geometry("600x620+50+50")
```

To test your change, run the app from the terminal in VS Code (`` Ctrl+` `` to open it):

```bash
python das_monitor.py
```

Or just double-click `run.bat` again.

### Other things you can customize

| What | Where to look | Example prompt for your AI assistant |
|---|---|---|
| **Window size/position** | `geometry("480x620+50+50")` | "Make the overlay 600px wide" |
| **Colors** | Color constants at the top | "Change the background to navy blue" |
| **Poll speed** | `POLL_INTERVAL = 1.0` | "Check for ticker changes every 0.5 seconds" |
| **News count** | `fetch_news_and_grok` | "Show 5 news headlines instead of 2" |
| **Platform support** | `find_montage_windows` | "Add support for Interactive Brokers TWS" |

### Adding support for other trading platforms

Ask your AI assistant something like:

> "Add support for [platform name] — it needs to detect the active ticker from the window title"

The AI will need to know how your platform formats its window titles. You can find out by asking:

> "Print all visible window titles on my screen so I can find my trading platform"

## Tech Stack

- **Python 3.10+** with tkinter (built-in GUI)
- **pywin32** (`win32gui`) for Windows window enumeration
- **requests** for API calls
- **python-dotenv** for loading `.env` files

No frameworks, no build tools, no npm. Just one Python file.

### Packages to install

```bash
pip install requests pywin32 python-dotenv
```

These are also listed in `requirements.txt` if you prefer `pip install -r requirements.txt`.

## License

MIT – do whatever you want with it.
