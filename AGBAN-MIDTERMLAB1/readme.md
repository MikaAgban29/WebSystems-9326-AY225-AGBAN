# 🎮 IGNScrape — Game Database Web Scraper

A web-based game data scraper that extracts structured information from **IGN.com's game database pages** and displays it in a clean, responsive interface.

Built with **Python + Flask + BeautifulSoup** for the backend and **HTML/CSS/JavaScript** for the frontend.

---

## 📌 Project Info

| Field | Details |
|---|---|
| **Course** | Web Systems and Technologies |
| **Section** | 9326-AY225 |
| **Student** | Agban, Mika |
| **Project** | Midterm Lab — Gaming Industry Web Scraper |

---

## 🎯 Features

- 🔍 Scrapes real game data from IGN.com game database pages
- 📋 Extracts 7 structured fields per game:
  - Game Title
  - Release Date
  - Key Features / Summary
  - Platform Availability
  - Developer
  - Publisher
  - IGN Score
- 💾 Saves scraped data to both `games.json` and `games.csv`
- 🔎 Search and filter results by keyword or platform
- 🃏 Grid and List view toggle
- 📱 Fully responsive design
- ⚠️ Gracefully handles missing fields with "Not Available"

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Scraping | BeautifulSoup4, Requests |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Data Storage | JSON file, CSV file |
| Fonts | Inter, Space Grotesk (Google Fonts) |

---

## 📁 Project Structure

```
AGBAN-MIDTERMLAB1/
│
├── app.py                  # Flask backend + scraping logic
├── games.json              # Scraped data (auto-generated)
├── games.csv               # Scraped data (auto-generated)
│
├── templates/
│   └── index.html          # Main HTML page
│
└── static/
    ├── script.js           # Frontend logic
    └── style.css           # Styling
```

---

## ⚙️ How to Run

### 1. Install dependencies
```bash
pip install flask requests beautifulsoup4 lxml
```

### 2. Start the server
```bash
python app.py
```
> On some systems use `py app.py` or `python3 app.py`

### 3. Open in browser
```
http://localhost:5000
```

---

## 🌐 How to Use

1. Paste any IGN game browse URL into the input field
2. Click **Scrape**
3. Wait for results to load
4. Use the **search bar** or **platform filter** to narrow results
5. Toggle between **Grid** and **List** view

### Suggested URLs to try:
| Label | URL |
|---|---|
| Top Rated Games | `https://www.ign.com/games?sort=score` |
| Top PS5 Games | `https://www.ign.com/games?sort=score&filter=ps5` |
| Top Switch Games | `https://www.ign.com/games?sort=score&filter=switch` |
| Top PC Games | `https://www.ign.com/games?sort=score&filter=pc` |
| Newest Releases | `https://www.ign.com/games?sort=release&direction=desc` |

---

## 📊 Data Fields

| Field | Source |
|---|---|
| `title` | `og:title` meta tag / `<h1>` |
| `release_date` | Summary box / JSON-LD schema |
| `key_features` | Game summary paragraph / `og:description` |
| `platform` | Platform icon `alt` attributes / JSON-LD |
| `developer` | Summary box "Developers" label |
| `publisher` | Summary box "Publishers" label |
| `score` | IGN score element |
| `image_url` | `og:image` meta tag |
| `source_url` | Original IGN game page URL |
| `scraped_at` | Timestamp of scrape (UTC) |

---

## ⚠️ Disclaimer

This project is for **educational purposes only**.
All game data belongs to [IGN.com](https://www.ign.com).
No data is redistributed or used commercially.