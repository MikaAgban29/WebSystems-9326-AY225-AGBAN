# 📚 GFG Python Scraper — Academic Learning Material Generator

A web-based system that scrapes Python programming articles from **GeeksforGeeks.org**
and generates a structured academic **PDF learning module**.

---

## 📌 Project Info

| Field | Details |
|---|---|
| **Course** | Web Systems and Technologies |
| **Section** | 9326-AY225 |
| **Student** | Agban, Mika |
| **Project** | GeeksforGeeks Academic Scraper |
| **Assigned Topic** | Python Programming |

---

## 🎯 Features

- 🔍 Scrapes Python articles dynamically from GeeksforGeeks
- 📋 Extracts 6 structured fields per article (zero hardcoded data)
- 💾 Saves data locally to `gfg_data.json` and `gfg_data.csv`
- 📄 Generates a professional academic PDF learning module
- 🔎 Search and filter articles by keyword or difficulty
- 📱 Responsive web interface

## 📊 Scraped Data Fields

| # | Field | Description |
|---|---|---|
| 1 | **Topic Title** | Main heading of the article |
| 2 | **Difficulty Level** | Easy / Medium / Hard |
| 3 | **Key Technical Concepts** | Introduction / core definition |
| 4 | **Code Snippets** | Python code examples |
| 5 | **Complexity Analysis** | Time & Space complexity |
| 6 | **Related Links** | References at end of article |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Scraping | BeautifulSoup4, Requests |
| PDF Generation | ReportLab |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Storage | JSON file, CSV file |
| Fonts | Lora, Outfit, JetBrains Mono |

---

## 📁 Project Structure

```
AGBAN-MIDTERMLAB2/
│
├── app.py                  # Flask backend + scraper + PDF generator
├── gfg_data.json           # Scraped data (auto-generated)
├── gfg_data.csv            # Scraped data (auto-generated)
├── requirements.txt
│
├── templates/
│   └── index.html
│
└── static/
    ├── script.js
    └── style.css
```

---

## ⚙️ How to Run

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## 📄 PDF Output Includes

- Cover page with metadata table
- Table of Contents
- Per-topic sections with difficulty badges
- Code blocks with syntax styling
- Complexity analysis tables
- Page numbers and footer