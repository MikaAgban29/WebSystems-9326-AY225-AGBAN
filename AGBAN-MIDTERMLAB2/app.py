from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
import os
from datetime import datetime
from io import BytesIO

# ── ReportLab PDF imports ──────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    PageBreak, Table, TableStyle, KeepTogether
)
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.colors import HexColor

app = Flask(__name__)

DATA_FILE = "gfg_data.json"
CSV_FILE  = "gfg_data.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

GFG_BASE = "https://www.geeksforgeeks.org"

# GFG Python category entry points
PYTHON_BROWSE_URLS = [
    "https://www.geeksforgeeks.org/python-programming-language/",
    "https://www.geeksforgeeks.org/python-tutorial/",
]

DIFFICULTY_KEYWORDS = {
    "easy":   ["beginner", "basic", "introduction", "intro", "getting started", "simple", "easy"],
    "medium": ["intermediate", "medium", "moderate"],
    "hard":   ["advanced", "hard", "complex", "difficult", "expert"],
}

COMPLEXITY_PATTERN = re.compile(
    r"(time\s+complexity|space\s+complexity|auxiliary\s+space)[^\n:]*[:：]\s*([O\(][\w\s\(\)\*\+\^logn,\s]+)",
    re.IGNORECASE
)


# ── helpers ───────────────────────────────────────────────────────────────────

def get_soup(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def infer_difficulty(title, text):
    combined = (title + " " + text).lower()
    for level, keywords in DIFFICULTY_KEYWORDS.items():
        if any(k in combined for k in keywords):
            return level.capitalize()
    return "Medium"  # default


def extract_code_snippets(article):
    """Extract code blocks from a GFG article."""
    snippets = []
    for block in article.find_all(["pre", "code", "div"],
                                   class_=re.compile(r"(code|syntax|highlight|python)", re.I)):
        text = clean(block.get_text())
        if len(text) > 20 and text not in snippets:
            snippets.append(text[:800])
        if len(snippets) >= 3:
            break
    return snippets


def extract_complexity(text):
    """Extract time/space complexity mentions."""
    results = {}
    for m in COMPLEXITY_PATTERN.finditer(text):
        label = clean(m.group(1)).lower()
        value = clean(m.group(2))
        if "time" in label and "time_complexity" not in results:
            results["time_complexity"] = value[:80]
        elif "space" in label or "auxiliary" in label:
            if "space_complexity" not in results:
                results["space_complexity"] = value[:80]
    return results


def extract_related_links(soup):
    """Extract reference / related links from article footer."""
    links = []
    seen = set()
    # GFG puts "References" or "Similar reads" near the bottom
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = clean(a.get_text())
        if (GFG_BASE in href or href.startswith("/")) and text and len(text) > 4:
            full = href if href.startswith("http") else GFG_BASE + href
            if full not in seen and "/python" in full.lower():
                seen.add(full)
                links.append({"text": text[:80], "url": full})
            if len(links) >= 5:
                break
    return links


# ── collect article links from GFG Python pages ───────────────────────────────

def collect_article_links(target=15):
    """Gather /python-* article URLs from GFG Python category pages."""
    links = []
    seen  = set()

    for browse_url in PYTHON_BROWSE_URLS:
        try:
            soup = get_soup(browse_url)
        except Exception:
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Must be a GFG python article (not a tag/category page)
            if not re.match(r"https?://(www\.)?geeksforgeeks\.org/[a-z0-9][a-z0-9-]+/?$", href):
                continue
            # Must relate to Python
            slug = href.rstrip("/").split("/")[-1]
            if "python" not in slug and "python" not in a.get_text().lower():
                continue
            if href in seen:
                continue
            # Skip category/tag pages
            if re.search(r"/(tag|category|page|quiz|mcq|interview|company)/", href):
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= target * 2:
                break

        if len(links) >= target * 2:
            break

    # fallback: use a well-known set of Python topic slugs if browse yields too few
    FALLBACK_SLUGS = [
        "python-lists", "python-tuples", "python-sets",
        "python-dictionary", "python-functions", "python-classes",
        "python-loops", "python-string-methods", "python-file-handling",
        "python-exception-handling", "python-lambda", "python-generators",
        "python-decorators", "python-comprehensions", "python-modules",
    ]
    for slug in FALLBACK_SLUGS:
        url = f"{GFG_BASE}/{slug}/"
        if url not in seen:
            seen.add(url)
            links.append(url)
        if len(links) >= target * 2:
            break

    return links[:target * 2]


# ── scrape a single GFG article ───────────────────────────────────────────────

def scrape_article(url):
    try:
        soup = get_soup(url)
    except Exception:
        return None

    # ── Title ──────────────────────────────────────────────────────────────────
    title = "Not Available"
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = re.sub(r"\s*[-–|]\s*(GeeksforGeeks|GfG).*$", "", og["content"], flags=re.I).strip()
    if not title or title == "Not Available":
        h1 = soup.find("h1")
        if h1:
            title = clean(h1.get_text())

    # Skip non-article pages
    if not title or len(title) < 5:
        return None

    # ── Article body ───────────────────────────────────────────────────────────
    article = (soup.find("article")
               or soup.find("div", class_=re.compile(r"article[-_]?body|entry[-_]?content|text", re.I))
               or soup.find("div", {"id": re.compile(r"article[-_]?content", re.I)})
               or soup.find("main"))

    if not article:
        article = soup

    full_text = clean(article.get_text(" "))

    # ── Difficulty ─────────────────────────────────────────────────────────────
    difficulty = "Not Available"
    diff_tag = soup.find(class_=re.compile(r"difficulty|level|badge", re.I))
    if diff_tag:
        dt = clean(diff_tag.get_text()).lower()
        for lvl in ["easy", "medium", "hard"]:
            if lvl in dt:
                difficulty = lvl.capitalize()
                break
    if difficulty == "Not Available":
        difficulty = infer_difficulty(title, full_text[:500])

    # ── Key Concepts / Introduction ────────────────────────────────────────────
    key_concepts = "Not Available"
    # Try: first meaningful paragraph after h1
    paras = article.find_all("p") if article else []
    for p in paras:
        t = clean(p.get_text())
        if len(t) > 60 and not re.search(r"cookie|subscribe|login|sign\s*up|advertisement", t, re.I):
            key_concepts = t[:600] + ("..." if len(t) > 600 else "")
            break

    # ── Code Snippets ──────────────────────────────────────────────────────────
    snippets = extract_code_snippets(article)
    code_snippet = snippets[0] if snippets else "Not Available"

    # ── Complexity ─────────────────────────────────────────────────────────────
    complexity = extract_complexity(full_text)
    time_complexity  = complexity.get("time_complexity",  "Not Available")
    space_complexity = complexity.get("space_complexity", "Not Available")

    # ── Related Links ──────────────────────────────────────────────────────────
    related = extract_related_links(soup)
    related_links = "; ".join(f"{r['text']} ({r['url']})" for r in related) if related else "Not Available"

    # ── Image ──────────────────────────────────────────────────────────────────
    image_url = None
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        image_url = og_img["content"].strip()

    return {
        "title": title,
        "url": url,
        "difficulty": difficulty,
        "key_concepts": key_concepts,
        "code_snippet": code_snippet,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "related_links": related_links,
        "image_url": image_url,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
    }


# ── PDF generator ──────────────────────────────────────────────────────────────

# Colour palette
C_GREEN      = HexColor("#2f8d46")   # GFG brand green
C_GREEN_DARK = HexColor("#1a5c2e")
C_GREEN_LIGHT= HexColor("#e8f5e9")
C_DARK       = HexColor("#1a1a2e")
C_GRAY       = HexColor("#4a4a6a")
C_LIGHT_GRAY = HexColor("#f4f4f8")
C_WHITE      = colors.white
C_CODE_BG    = HexColor("#f0f4f0")
C_ACCENT     = HexColor("#ff6b35")


def build_styles():
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "cover_title": ps("cover_title",
            fontName="Helvetica-Bold", fontSize=32,
            textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=8, leading=40),
        "cover_sub": ps("cover_sub",
            fontName="Helvetica", fontSize=14,
            textColor=HexColor("#c8e6c9"), alignment=TA_CENTER, spaceAfter=6),
        "cover_meta": ps("cover_meta",
            fontName="Helvetica", fontSize=11,
            textColor=HexColor("#a5d6a7"), alignment=TA_CENTER, spaceAfter=4),
        "toc_title": ps("toc_title",
            fontName="Helvetica-Bold", fontSize=18,
            textColor=C_GREEN_DARK, spaceAfter=10, spaceBefore=6),
        "toc_item": ps("toc_item",
            fontName="Helvetica", fontSize=11,
            textColor=C_DARK, spaceAfter=4, leftIndent=12),
        "chapter_num": ps("chapter_num",
            fontName="Helvetica-Bold", fontSize=11,
            textColor=C_GREEN, spaceAfter=2),
        "chapter_title": ps("chapter_title",
            fontName="Helvetica-Bold", fontSize=20,
            textColor=C_GREEN_DARK, spaceAfter=6, spaceBefore=4, leading=24),
        "section_head": ps("section_head",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=C_GREEN_DARK, spaceAfter=4, spaceBefore=10,
            borderPad=4),
        "body": ps("body",
            fontName="Helvetica", fontSize=10.5,
            textColor=C_DARK, spaceAfter=6, leading=16, alignment=TA_JUSTIFY),
        "code": ps("code",
            fontName="Courier", fontSize=8.5,
            textColor=HexColor("#1b5e20"), spaceAfter=4, leading=13,
            leftIndent=8, rightIndent=8, backColor=C_CODE_BG,
            borderPad=6, wordWrap="CJK"),
        "badge_easy":   ps("badge_easy",   fontName="Helvetica-Bold", fontSize=10, textColor=HexColor("#2e7d32")),
        "badge_medium": ps("badge_medium", fontName="Helvetica-Bold", fontSize=10, textColor=HexColor("#e65100")),
        "badge_hard":   ps("badge_hard",   fontName="Helvetica-Bold", fontSize=10, textColor=HexColor("#b71c1c")),
        "label": ps("label",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=C_GRAY, spaceAfter=2),
        "footer_text": ps("footer_text",
            fontName="Helvetica", fontSize=8,
            textColor=HexColor("#9e9e9e"), alignment=TA_CENTER),
        "url_style": ps("url_style",
            fontName="Helvetica-Oblique", fontSize=9,
            textColor=C_GREEN, spaceAfter=3),
    }


def draw_page_frame(canvas, doc):
    """Header + footer on every page."""
    w, h = A4
    canvas.saveState()

    # Top green bar
    canvas.setFillColor(C_GREEN)
    canvas.rect(0, h - 14*mm, w, 14*mm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(20*mm, h - 9*mm, "GeeksforGeeks Python Learning Module")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - 20*mm, h - 9*mm, f"Generated: {datetime.now().strftime('%B %d, %Y')}")

    # Bottom bar
    canvas.setFillColor(C_GREEN_DARK)
    canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20*mm, 3.5*mm, "Generated by IGNScrape Academic System  |  For Educational Purposes Only")
    canvas.drawRightString(w - 20*mm, 3.5*mm, f"Page {doc.page}")

    canvas.restoreState()


def draw_cover_frame(canvas, doc):
    """Cover page — full green background, no header/footer bars."""
    w, h = A4
    canvas.saveState()

    # Deep green gradient background (simulated with layered rects)
    canvas.setFillColor(C_GREEN_DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#246b38"))
    canvas.rect(0, h * 0.45, w, h * 0.55, fill=1, stroke=0)

    # Decorative circles
    canvas.setFillColor(HexColor("#ffffff15"))
    canvas.circle(w * 0.85, h * 0.15, 80, fill=1, stroke=0)
    canvas.circle(w * 0.1, h * 0.85, 60, fill=1, stroke=0)
    canvas.circle(w * 0.5, h * 0.05, 40, fill=1, stroke=0)

    # Horizontal accent bar
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h * 0.48, w, 4, fill=1, stroke=0)

    canvas.restoreState()


def generate_pdf(articles, student_name="Student"):
    buf = BytesIO()
    styles = build_styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title="Python Learning Module",
        author=student_name,
    )

    story = []

    # ── COVER PAGE ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*cm))
    story.append(Paragraph("PYTHON PROGRAMMING", styles["cover_sub"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Learning Module", styles["cover_title"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("GeeksforGeeks Academic Series", styles["cover_sub"]))
    story.append(Spacer(1, 2*cm))

    # Info table on cover
    cover_data = [
        ["Topics Covered", str(len(articles))],
        ["Subject Category", "Python Programming"],
        ["Generated By", student_name],
        ["Date of Generation", datetime.now().strftime("%B %d, %Y")],
        ["Source", "GeeksforGeeks.org"],
    ]
    tbl = Table(cover_data, colWidths=[5.5*cm, 9*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), HexColor("#1a5c2e")),
        ("BACKGROUND",  (1, 0), (1, -1), HexColor("#ffffff18")),
        ("TEXTCOLOR",   (0, 0), (-1, -1), C_WHITE),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [HexColor("#1a5c2e"), HexColor("#246b38")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor("#4caf5060")),
        ("PADDING",     (0, 0), (-1, -1), 8),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(tbl)

    story.append(PageBreak())

    # ── TABLE OF CONTENTS ─────────────────────────────────────────────────────
    doc2_pages = [draw_page_frame]  # reuse for all subsequent pages

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Table of Contents", styles["toc_title"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_GREEN, spaceAfter=12))

    for i, art in enumerate(articles, 1):
        diff = art.get("difficulty", "N/A")
        diff_colors = {"Easy": "#2e7d32", "Medium": "#e65100", "Hard": "#b71c1c"}
        dc = diff_colors.get(diff, "#555")
        story.append(Paragraph(
            f'<font color="#2f8d46"><b>{i:02d}.</b></font>  {art["title"]}'
            f'  <font color="{dc}" size="8">[{diff}]</font>',
            styles["toc_item"]
        ))

    story.append(PageBreak())

    # ── ARTICLE PAGES ─────────────────────────────────────────────────────────
    for idx, art in enumerate(articles, 1):
        items = []

        # Chapter number + title
        items.append(Paragraph(f"Topic {idx:02d} of {len(articles)}", styles["chapter_num"]))

        safe_title = art["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items.append(Paragraph(safe_title, styles["chapter_title"]))

        # Difficulty badge + source URL row
        diff      = art.get("difficulty", "Not Available")
        badge_sty = {
            "Easy":   styles["badge_easy"],
            "Medium": styles["badge_medium"],
            "Hard":   styles["badge_hard"],
        }.get(diff, styles["badge_medium"])

        diff_colors_hex = {"Easy": "#e8f5e9", "Medium": "#fff3e0", "Hard": "#ffebee"}
        diff_text_hex   = {"Easy": "#2e7d32", "Medium": "#e65100", "Hard": "#c62828"}
        dbg = diff_colors_hex.get(diff, "#f5f5f5")
        dtx = diff_text_hex.get(diff, "#333")

        badge_tbl = Table(
            [[Paragraph(f'<font color="{dtx}"><b>⬤  {diff}</b></font>', badge_sty),
              Paragraph(f'<font color="#2f8d46">{art["url"]}</font>', styles["url_style"])]],
            colWidths=[3.5*cm, 13*cm]
        )
        badge_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), HexColor(dbg)),
            ("PADDING",    (0,0), (-1,-1), 6),
            ("ROUNDEDCORNERS", [4]),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ]))
        items.append(badge_tbl)
        items.append(Spacer(1, 0.3*cm))
        items.append(HRFlowable(width="100%", thickness=1, color=C_GREEN_LIGHT, spaceAfter=8))

        # ── Key Concepts ────────────────────────────────────────────────────
        items.append(Paragraph("📘  Key Technical Concepts", styles["section_head"]))
        kc = (art.get("key_concepts") or "Not Available").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items.append(Paragraph(kc, styles["body"]))

        # ── Code Snippet ────────────────────────────────────────────────────
        items.append(Paragraph("💻  Code Snippet / Implementation", styles["section_head"]))
        code = art.get("code_snippet", "Not Available")
        if code and code != "Not Available":
            # Escape XML special chars in code
            code_safe = (code.replace("&", "&amp;")
                             .replace("<", "&lt;")
                             .replace(">", "&gt;")
                             .replace('"', "&quot;"))
            code_tbl = Table(
                [[Paragraph(code_safe, styles["code"])]],
                colWidths=[16.5*cm]
            )
            code_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), C_CODE_BG),
                ("BOX",        (0,0), (-1,-1), 1, C_GREEN),
                ("LEFTPADDING", (0,0), (-1,-1), 10),
                ("RIGHTPADDING",(0,0), (-1,-1), 10),
                ("TOPPADDING",  (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
                ("ROUNDEDCORNERS", [4]),
            ]))
            items.append(code_tbl)
        else:
            items.append(Paragraph("Not Available", styles["body"]))

        # ── Complexity ──────────────────────────────────────────────────────
        items.append(Paragraph("⏱  Complexity Analysis", styles["section_head"]))
        tc = art.get("time_complexity",  "Not Available")
        sc = art.get("space_complexity", "Not Available")
        cx_data = [
            [Paragraph("<b>Time Complexity</b>",  styles["label"]),
             Paragraph("<b>Space Complexity</b>", styles["label"])],
            [Paragraph(tc, styles["body"]),
             Paragraph(sc, styles["body"])],
        ]
        cx_tbl = Table(cx_data, colWidths=[8*cm, 8.5*cm])
        cx_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), C_GREEN_LIGHT),
            ("BACKGROUND",  (0,1), (-1,-1), C_LIGHT_GRAY),
            ("BOX",         (0,0), (-1,-1), 0.5, C_GREEN),
            ("INNERGRID",   (0,0), (-1,-1), 0.5, HexColor("#c8e6c9")),
            ("PADDING",     (0,0), (-1,-1), 8),
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ]))
        items.append(cx_tbl)

        # ── References / Related Links ───────────────────────────────────────
        items.append(Paragraph("🔗  References &amp; Related Links", styles["section_head"]))
        rl = art.get("related_links", "Not Available")
        if rl and rl != "Not Available":
            for link_str in rl.split(";")[:5]:
                link_str = link_str.strip()
                if link_str:
                    safe_link = link_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    items.append(Paragraph(f"• {safe_link}", styles["url_style"]))
        else:
            items.append(Paragraph("Not Available", styles["body"]))

        items.append(Spacer(1, 0.4*cm))

        story.append(KeepTogether(items[:6]))   # keep title + difficulty + intro together
        for item in items[6:]:
            story.append(item)

        if idx < len(articles):
            story.append(PageBreak())

    # Build with cover page frame for page 1, normal frame for rest
    def on_first_page(canvas, doc):
        draw_cover_frame(canvas, doc)

    def on_later_pages(canvas, doc):
        draw_page_frame(canvas, doc)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Load cached data if available
    cached = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            cached = json.load(f)
    return render_template("index.html", cached_count=len(cached))


@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        data   = request.get_json(force=True, silent=True) or {}
        target = max(10, min(int(data.get("count", 15)), 25))

        links = collect_article_links(target)
        if not links:
            return jsonify({"error": "Could not discover any GFG Python articles."}), 500

        articles = []
        for url in links:
            if len(articles) >= target:
                break
            art = scrape_article(url)
            if art and art["title"] != "Not Available":
                articles.append(art)
            time.sleep(0.8)

        if not articles:
            return jsonify({"error": "No articles could be scraped. Try again."}), 500

        # Persist
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        fields = ["title","url","difficulty","key_concepts","code_snippet",
                  "time_complexity","space_complexity","related_links","scraped_at"]
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(articles)

        return jsonify({"articles": articles, "count": len(articles)})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Scraping error: {str(e)}"}), 500


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf_route():
    try:
        data    = request.get_json(force=True, silent=True) or {}
        student = data.get("student_name", "Student").strip() or "Student"

        # Use cached data
        if not os.path.exists(DATA_FILE):
            return jsonify({"error": "No scraped data found. Please scrape first."}), 400

        with open(DATA_FILE, encoding="utf-8") as f:
            articles = json.load(f)

        if not articles:
            return jsonify({"error": "Scraped data is empty. Please scrape again."}), 400

        pdf_buf = generate_pdf(articles, student_name=student)
        filename = f"Python_Learning_Module_{datetime.now().strftime('%Y%m%d')}.pdf"

        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"PDF error: {str(e)}"}), 500


@app.route("/load-cache", methods=["GET"])
def load_cache():
    if not os.path.exists(DATA_FILE):
        return jsonify({"articles": [], "count": 0})
    with open(DATA_FILE, encoding="utf-8") as f:
        articles = json.load(f)
    return jsonify({"articles": articles, "count": len(articles)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)