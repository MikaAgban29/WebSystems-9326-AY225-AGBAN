from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
from datetime import datetime

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

IGN_DOMAIN = "https://www.ign.com"

# Maps img alt text / visible text → normalised platform name
PLATFORM_ALT_MAP = {
    "playstation 5": "PlayStation 5",
    "playstation 4": "PlayStation 4",
    "ps5": "PlayStation 5",
    "ps4": "PlayStation 4",
    "xbox series x": "Xbox Series X",
    "xbox series s": "Xbox Series S",
    "xbox series x/s": "Xbox Series X/S",
    "xbox one": "Xbox One",
    "nintendo switch": "Nintendo Switch",
    "nintendo switch 2": "Nintendo Switch 2",
    "pc": "PC",
    "windows": "PC",
    "steam": "PC",
    "ios": "iOS",
    "iphone": "iOS",
    "android": "Android",
    "macos": "macOS",
    "mac": "macOS",
}

PLATFORM_PATTERN = re.compile(
    r"\b(PlayStation\s*5|PlayStation\s*4|PS5|PS4|Xbox Series [XS/]+|Xbox One|"
    r"Nintendo Switch(?:\s*2)?|PC|Steam|iOS|Android|macOS|Mac)\b",
    re.IGNORECASE,
)

LABEL_MAP = {
    "developer": "developer",
    "developers": "developer",
    "publisher": "publisher",
    "publishers": "publisher",
    "genre": "genre",
    "genres": "genre",
    "platform": "platform",
    "platforms": "platform",
    "release date": "release_date",
    "released": "release_date",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def get_soup(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def clean_text(t):
    return re.sub(r"\s+", " ", t or "").strip()


def extract_og_image(soup):
    for prop in ("og:image", "twitter:image"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def normalise_platform_list(raw_list):
    seen, out = set(), []
    for p in raw_list:
        norm = PLATFORM_ALT_MAP.get(p.strip().lower(), p.strip())
        key = norm.lower()
        if key not in seen:
            seen.add(key)
            out.append(norm)
    return ", ".join(out[:6])


# ── core IGN metadata extractor ───────────────────────────────────────────────
# IGN's Summary box layout (as of 2025-2026):
#
#   <section> or <div>
#     <p class="...">Summary text here...</p>
#     <div>  ← metadata columns
#       <div><p><b>Developers</b></p>  <p><a>Studio Name</a></p></div>
#       <div><p><b>Release Date</b></p><p>Feb. 12, 2026</p></div>
#       <div><p><b>Publishers</b></p>  <p><a>Publisher Name</a></p></div>
#       <div><p><b>Platforms</b></p>   <p><img alt="PlayStation 5">…</p></div>
#     </div>
#   </section>

def extract_ign_summary_box(soup):
    info = {
        "developer": "Not Available",
        "publisher": "Not Available",
        "platform": "Not Available",
        "release_date": "Not Available",
        "summary": "Not Available",
    }

    # ── STRATEGY 1: Find label tags (bold/strong/p containing label text) ──────
    # Walk every element; if its full trimmed text matches a known label exactly,
    # grab the text/img content from the next sibling or parent's next sibling.

    def try_extract_after(label_tag, field):
        """Try to read the value that follows label_tag in the DOM."""
        candidates = []

        # a) direct next siblings of the label tag
        for sib in label_tag.find_next_siblings():
            t = clean_text(sib.get_text())
            if t:
                candidates.append((sib, t))
            if candidates:
                break

        # b) parent's next sibling (common IGN pattern: label in <p>, value in next <p>)
        if not candidates and label_tag.parent:
            for sib in label_tag.parent.find_next_siblings():
                t = clean_text(sib.get_text())
                if t:
                    candidates.append((sib, t))
                if candidates:
                    break

        # c) grandparent's next sibling div/p
        if not candidates and label_tag.parent and label_tag.parent.parent:
            for sib in label_tag.parent.parent.find_next_siblings():
                t = clean_text(sib.get_text())
                if t:
                    candidates.append((sib, t))
                if candidates:
                    break

        for (tag, text) in candidates:
            if not text or len(text) > 300:
                continue
            # Skip if the "value" is just another label
            if text.lower().rstrip("s").rstrip(":") in LABEL_MAP:
                continue

            if field == "platform":
                # Extract platform names from img alt attributes
                plats = []
                seen_p = set()
                for img in tag.find_all("img", alt=True):
                    norm = PLATFORM_ALT_MAP.get(img["alt"].strip().lower())
                    if norm and norm.lower() not in seen_p:
                        seen_p.add(norm.lower())
                        plats.append(norm)
                if plats:
                    return ", ".join(plats)
                # Fallback: parse text for known platform names
                found = PLATFORM_PATTERN.findall(text)
                if found:
                    return normalise_platform_list(found)
                return text  # use raw text if nothing else

            return text

        return None

    # Search for all elements whose complete text equals a label keyword
    for tag in soup.find_all(True):
        raw = clean_text(tag.get_text())
        label = raw.lower().rstrip(":")
        field = LABEL_MAP.get(label)
        if not field or field not in info:
            continue
        if info[field] != "Not Available":
            continue
        # Avoid matching huge containers that just happen to contain the word
        if len(raw) > 40:
            continue

        val = try_extract_after(tag, field)
        if val:
            info[field] = val[:250]

    # ── STRATEGY 2: dt / dd pairs ─────────────────────────────────────────────
    for dt in soup.find_all("dt"):
        label = clean_text(dt.get_text()).lower().rstrip(":")
        field = LABEL_MAP.get(label)
        if not field or field not in info or info[field] != "Not Available":
            continue
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        if field == "platform":
            plats = []
            seen_p = set()
            for img in dd.find_all("img", alt=True):
                norm = PLATFORM_ALT_MAP.get(img["alt"].strip().lower(), img["alt"].strip())
                if norm.lower() not in seen_p:
                    seen_p.add(norm.lower())
                    plats.append(norm)
            if plats:
                info["platform"] = ", ".join(plats)
                continue
        val = clean_text(dd.get_text())
        if val:
            info[field] = val[:250]

    # ── STRATEGY 3: JSON-LD VideoGame schema ──────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, list):
                ld = ld[0]
            if not isinstance(ld, dict):
                continue

            game_obj = None
            if ld.get("@type") in ("VideoGame", "Game"):
                game_obj = ld
            else:
                for node in ld.get("@graph", []):
                    if isinstance(node, dict) and node.get("@type") in ("VideoGame", "Game"):
                        game_obj = node
                        break
            if not game_obj:
                continue

            def get_name_field(obj):
                if isinstance(obj, dict):
                    return obj.get("name", "")
                if isinstance(obj, list):
                    parts = []
                    for x in obj[:4]:
                        parts.append(x.get("name", str(x)) if isinstance(x, dict) else str(x))
                    return ", ".join(parts)
                return str(obj) if obj else ""

            if info["developer"] == "Not Available":
                v = get_name_field(game_obj.get("author") or game_obj.get("developer"))
                if v:
                    info["developer"] = v

            if info["publisher"] == "Not Available":
                v = get_name_field(game_obj.get("publisher"))
                if v:
                    info["publisher"] = v

            if info["release_date"] == "Not Available":
                rd = game_obj.get("datePublished") or game_obj.get("releaseDate")
                if rd:
                    info["release_date"] = str(rd)[:10]

            if info["platform"] == "Not Available":
                gp = game_obj.get("gamePlatform") or game_obj.get("operatingSystem")
                if isinstance(gp, list):
                    info["platform"] = ", ".join(str(x) for x in gp[:6])
                elif isinstance(gp, str):
                    info["platform"] = gp

            if info["summary"] == "Not Available":
                desc = game_obj.get("description")
                if desc and len(desc) > 30:
                    info["summary"] = clean_text(desc)[:400]

        except Exception:
            continue

    # ── STRATEGY 4: line-by-line text scan ────────────────────────────────────
    # Get the page as newline-separated text and look for "Label\nValue" patterns
    if info["developer"] == "Not Available" or info["publisher"] == "Not Available":
        lines = [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]
        for i, line in enumerate(lines):
            lc = line.lower().rstrip(":")
            field = LABEL_MAP.get(lc)
            if not field or field not in info or info[field] != "Not Available":
                continue
            # The value should be on the very next non-empty line
            if i + 1 < len(lines):
                val = lines[i + 1].strip()
                if val and len(val) < 150 and val.lower().rstrip(":") not in LABEL_MAP:
                    info[field] = val

    # ── STRATEGY 5: img alt fallback for platform ─────────────────────────────
    if info["platform"] == "Not Available":
        plats, seen_p = [], set()
        for img in soup.find_all("img", alt=True):
            norm = PLATFORM_ALT_MAP.get(img["alt"].strip().lower())
            if norm and norm.lower() not in seen_p:
                seen_p.add(norm.lower())
                plats.append(norm)
        if plats:
            info["platform"] = ", ".join(plats[:6])

    # ── STRATEGY 6: regex scan on full page text ──────────────────────────────
    if info["platform"] == "Not Available":
        page_text = soup.get_text(" ", strip=True)
        found = PLATFORM_PATTERN.findall(page_text)
        if found:
            info["platform"] = normalise_platform_list(found)

    return info


# ── scrape a single IGN game detail page ─────────────────────────────────────

def scrape_ign_game_page(url):
    try:
        soup = get_soup(url)
    except Exception:
        return None

    # Title
    title = "Not Available"
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = re.sub(r"\s*[-–|]\s*IGN.*$", "", og_title["content"], flags=re.I).strip()
    if not title or title == "Not Available":
        h1 = soup.find("h1")
        if h1:
            title = clean_text(h1.get_text())

    # Image
    image_url = extract_og_image(soup)

    # Metadata
    info = extract_ign_summary_box(soup)

    # Key Features — prefer the actual summary blurb over SEO meta
    key_features = info.get("summary", "Not Available")

    if key_features == "Not Available":
        # Look for a visible summary paragraph near a "Summary" heading
        summary_h = soup.find(
            lambda t: t.name in ["h2", "h3", "h4", "p", "span", "div"]
            and clean_text(t.get_text()).lower() == "summary"
        )
        if summary_h:
            sib = summary_h.find_next_sibling()
            while sib:
                t = clean_text(sib.get_text())
                if len(t) > 40 and t.lower() not in LABEL_MAP:
                    key_features = t[:400] + ("..." if len(t) > 400 else "")
                    break
                sib = sib.find_next_sibling()

    if key_features == "Not Available":
        container = soup.find("main") or soup.find("article") or soup
        for p in container.find_all("p"):
            t = clean_text(p.get_text())
            if len(t) > 80 and not re.search(
                r"cookie|privacy|subscribe|advertisement|release date|trailers|news|reviews|guides",
                t, re.I
            ):
                key_features = t[:400] + ("..." if len(t) > 400 else "")
                break

    if key_features == "Not Available":
        og_desc = (soup.find("meta", property="og:description")
                   or soup.find("meta", attrs={"name": "description"}))
        if og_desc and og_desc.get("content"):
            raw = clean_text(og_desc["content"])
            # Reject the generic IGN template description
            if not re.search(r"release date.*trailers.*news.*reviews.*guides", raw, re.I):
                key_features = raw[:400]

    # Score
    score = "Not Available"
    for finder in [
        lambda s: s.find(attrs={"data-cy": re.compile(r"score", re.I)}),
        lambda s: s.find(class_=re.compile(r"\bscore\b|\brating\b", re.I)),
    ]:
        tag = finder(soup)
        if tag:
            st = clean_text(tag.get_text())
            if re.match(r"^\d+(\.\d+)?(/\d+)?$", st):
                score = st
                break

    return {
        "title": title,
        "image_url": image_url,
        "release_date": info["release_date"],
        "key_features": key_features,
        "platform": info["platform"],
        "developer": info["developer"],
        "publisher": info["publisher"],
        "score": score,
        "source_url": url,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
    }


# ── link discovery ────────────────────────────────────────────────────────────

def collect_game_links(soup, target):
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = href if href.startswith("http") else IGN_DOMAIN + href
        if not re.match(r"https?://(www\.)?ign\.com/games/[a-z0-9][a-z0-9-]+$", full):
            continue
        if full not in seen:
            seen.add(full)
            links.append(full)
        if len(links) >= target * 2:
            break
    return links


def extract_inline_games(soup, page_url, target):
    games, seen = [], set()
    time_tag = soup.find("time")
    article_date = ""
    if time_tag:
        dt_val = time_tag.get("datetime", "")
        article_date = dt_val[:10] if dt_val else time_tag.get_text(strip=True)[:10]

    for heading in soup.find_all(["h2", "h3"]):
        raw = clean_text(heading.get_text())
        if len(raw) < 2 or len(raw.split()) > 10:
            continue
        if re.search(r"(best|top|how|why|what|guide|tip|review|intro|faq|more|also)", raw, re.I):
            continue
        tk = raw.lower()
        if tk in seen:
            continue
        seen.add(tk)

        paragraphs, sib = [], heading.find_next_sibling()
        while sib and sib.name not in ["h2", "h3"]:
            if sib.name == "p":
                t = clean_text(sib.get_text())
                if len(t) > 30:
                    paragraphs.append(t)
            sib = sib.find_next_sibling()

        key_features = "Not Available"
        if paragraphs:
            combined = " ".join(paragraphs[:2])
            key_features = combined[:350] + ("..." if len(combined) > 350 else "")

        plats = PLATFORM_PATTERN.findall(key_features) if key_features != "Not Available" else []
        platform = normalise_platform_list(plats) if plats else "Not Available"

        games.append({
            "title": raw,
            "image_url": None,
            "release_date": article_date,
            "key_features": key_features,
            "platform": platform,
            "developer": "Not Available",
            "publisher": "Not Available",
            "score": "Not Available",
            "source_url": page_url,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
        })
        if len(games) >= target:
            break
    return games


# ── orchestrator ──────────────────────────────────────────────────────────────

def scrape_ign(url, target=25):
    soup = get_soup(url)

    is_game_page = bool(re.match(r"https?://(www\.)?ign\.com/games/[a-z0-9][a-z0-9-]+$", url))
    if is_game_page:
        game = scrape_ign_game_page(url)
        return [game] if game else []

    links = collect_game_links(soup, target)

    games = []
    for link in links:
        if len(games) >= target:
            break
        game = scrape_ign_game_page(link)
        if game and game["title"] not in ("Not Available", ""):
            games.append(game)
        time.sleep(0.7)

    if not games:
        games = extract_inline_games(soup, url, target)

    return games[:target]


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = data.get("url", "").strip()
        target = max(10, min(int(data.get("count", 25)), 50))

        if not url:
            return jsonify({"error": "No URL provided."}), 400

        if not re.match(r"https?://(www\.)?ign\.com", url):
            return jsonify({"error": "Only IGN.com URLs are supported."}), 400

        blocked = re.match(
            r"https?://(www\.)?ign\.com/(articles|videos|news|reviews|wikis|"
            r"watch|podcasts|scores|slideshows|boards|faqs)/",
            url
        )
        if blocked:
            return jsonify({
                "error": (
                    "That page is an article/news/review — not a game database page. "
                    "Try ign.com/games or ign.com/games?sort=score to browse actual games."
                )
            }), 400

        try:
            games = scrape_ign(url, target)
        except Exception as e:
            return jsonify({"error": f"Scraping error: {str(e)}"}), 500

        if not games:
            return jsonify({
                "error": (
                    "No games found on that page. "
                    "Try ign.com/games or ign.com/games?sort=score&filter=ps5"
                )
            }), 500

        with open("games.json", "w", encoding="utf-8") as f:
            json.dump(games, f, indent=2, ensure_ascii=False)

        with open("games.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=games[0].keys())
            writer.writeheader()
            writer.writerows(games)

        return jsonify({"games": games, "count": len(games)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)