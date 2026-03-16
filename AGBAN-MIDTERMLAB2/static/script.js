let allArticles = [];

// ── on load: check for cached data ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/load-cache');
    const data = await res.json();
    if (data.articles && data.articles.length > 0) {
      document.getElementById('cache-badge').textContent =
        `${data.articles.length} articles cached`;
      document.getElementById('topbar-status').textContent =
        `${data.articles.length} articles in cache`;
      loadArticles(data.articles);
    }
  } catch (e) { /* no cache */ }
});

function adjustCount(delta) {
  const inp = document.getElementById('count-input');
  let val = parseInt(inp.value) + delta;
  val = Math.max(10, Math.min(25, val));
  inp.value = val;
}

// ── scraping ──────────────────────────────────────────────────────────────────
async function startScrape() {
  const btn   = document.getElementById('scrape-btn');
  const count = parseInt(document.getElementById('count-input').value) || 12;

  document.getElementById('error-box').style.display  = 'none';
  document.getElementById('progress-wrap').style.display = 'block';
  btn.disabled = true;
  document.getElementById('btn-icon').textContent = '⏳';
  document.getElementById('btn-text').textContent = 'Scraping…';
  document.getElementById('topbar-status').textContent = 'Scraping GFG…';

  // Animate steps
  let prog = 5;
  setStep(1, 'active');
  setFill(prog);
  setLabel('Collecting article links…');

  const progTimer = setInterval(() => {
    prog = Math.min(prog + 1.5, 88);
    setFill(prog);
    if (prog > 30 && prog < 50) {
      setStep(1, 'done'); setStep(2, 'active');
      setLabel('Fetching article content…');
    }
    if (prog >= 70) {
      setStep(2, 'done'); setStep(3, 'active');
      setLabel('Saving data to JSON & CSV…');
    }
  }, 600);

  try {
    const res  = await fetch('/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count })
    });
    const data = await res.json();
    clearInterval(progTimer);

    if (!res.ok || data.error) {
      showError(data.error || 'Scraping failed.');
    } else {
      setStep(3, 'done');
      setFill(100);
      setLabel(`✓ Done! ${data.count} articles scraped and saved.`);
      document.getElementById('cache-badge').textContent = `${data.count} articles cached`;
      document.getElementById('topbar-status').textContent = `${data.count} articles ready`;
      setTimeout(() => {
        document.getElementById('progress-wrap').style.display = 'none';
      }, 2000);
      loadArticles(data.articles);
    }
  } catch (e) {
    clearInterval(progTimer);
    showError('Server error: ' + e.message);
  }

  btn.disabled = false;
  document.getElementById('btn-icon').textContent = '▶';
  document.getElementById('btn-text').textContent = 'Start Scraping';
}

function setStep(n, state) {
  const el = document.getElementById(`step-${n}`);
  if (!el) return;
  el.className = 'step ' + state;
}
function setFill(pct) {
  document.getElementById('progress-fill').style.width = pct + '%';
}
function setLabel(txt) {
  document.getElementById('progress-label').textContent = txt;
}
function showError(msg) {
  document.getElementById('error-text').textContent = msg;
  document.getElementById('error-box').style.display  = 'flex';
  document.getElementById('progress-wrap').style.display = 'none';
  document.getElementById('topbar-status').textContent = 'Error';
}

// ── load & display articles ───────────────────────────────────────────────────
function loadArticles(articles) {
  allArticles = articles;

  // Stats
  const easy   = articles.filter(a => a.difficulty === 'Easy').length;
  const medium = articles.filter(a => a.difficulty === 'Medium').length;
  const hard   = articles.filter(a => a.difficulty === 'Hard').length;
  const withCode = articles.filter(a => a.code_snippet && a.code_snippet !== 'Not Available').length;

  animateNum('s-total',  articles.length);
  animateNum('s-easy',   easy);
  animateNum('s-medium', medium);
  animateNum('s-hard',   hard);
  animateNum('s-code',   withCode);

  document.getElementById('stats-bar').style.display    = 'flex';
  document.getElementById('results').style.display      = 'block';
  document.getElementById('result-count').textContent   = articles.length;
  renderArticles(articles);
  document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function animateNum(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let cur = 0;
  const step = Math.max(1, Math.ceil(target / 20));
  const t = setInterval(() => {
    cur = Math.min(cur + step, target);
    el.textContent = cur;
    if (cur >= target) clearInterval(t);
  }, 40);
}

function filterArticles() {
  const q    = document.getElementById('search-box').value.toLowerCase();
  const diff = document.getElementById('diff-filter').value.toLowerCase();
  const filtered = allArticles.filter(a => {
    const mQ = !q || [a.title, a.key_concepts, a.code_snippet, a.difficulty]
      .some(f => f && f.toLowerCase().includes(q));
    const mD = !diff || (a.difficulty && a.difficulty.toLowerCase() === diff);
    return mQ && mD;
  });
  document.getElementById('result-count').textContent = filtered.length;
  renderArticles(filtered);
}

function esc(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderArticles(articles) {
  const grid = document.getElementById('article-grid');
  if (!articles.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="e-icon">📭</div>
        <h3>No articles match</h3>
        <p>Try a different search term or filter.</p>
      </div>`;
    return;
  }

  grid.innerHTML = articles.map((a, i) => {
    const na     = v => v && v !== 'Not Available' ? v : null;
    const diff   = a.difficulty || 'Medium';
    const dlc    = diff.toLowerCase();
    const dclass = `diff-badge diff-${dlc}`;

    const tc = na(a.time_complexity)  || 'N/A';
    const sc = na(a.space_complexity) || 'N/A';
    const tcClass = tc === 'N/A' ? 'na' : '';
    const scClass = sc === 'N/A' ? 'na' : '';

    const codeHtml = na(a.code_snippet)
      ? `<div class="card-code">${esc(a.code_snippet.slice(0, 200))}</div>`
      : `<span style="font-size:12px;color:var(--ink-light);font-style:italic">Not Available</span>`;

    const scraped = a.scraped_at
      ? new Date(a.scraped_at).toLocaleDateString('en-US', {month:'short',day:'numeric',year:'numeric'})
      : '';

    return `
      <div class="article-card" style="animation-delay:${i * 35}ms">
        <div class="card-top">
          <div class="card-title-row">
            <div class="card-title">${esc(a.title)}</div>
            <span class="${dclass}">${diff}</span>
          </div>
          <a class="card-url" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.url)}</a>
        </div>
        <div class="card-body">
          <div>
            <div class="card-section-label">💡 Key Concepts</div>
            <div class="card-text">${esc(na(a.key_concepts) || 'Not available')}</div>
          </div>
          <div>
            <div class="card-section-label">💻 Code Snippet</div>
            ${codeHtml}
          </div>
          <div>
            <div class="card-section-label">⏱ Complexity</div>
            <div class="complexity-row">
              <div class="cx-box">
                <div class="cx-label">Time</div>
                <div class="cx-val ${tcClass}">${esc(tc)}</div>
              </div>
              <div class="cx-box">
                <div class="cx-label">Space</div>
                <div class="cx-val ${scClass}">${esc(sc)}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="card-footer">
          <a class="view-btn" href="${esc(a.url)}" target="_blank" rel="noopener">
            Read on GFG →
          </a>
          ${scraped ? `<span class="scraped-date">${scraped}</span>` : ''}
        </div>
      </div>`;
  }).join('');
}

// ── PDF generation ────────────────────────────────────────────────────────────
async function generatePDF() {
  const btn     = document.getElementById('pdf-btn');
  const status  = document.getElementById('pdf-status');
  const student = document.getElementById('student-name').value.trim() || 'Student';

  if (allArticles.length === 0) {
    status.className = 'export-note error';
    status.textContent = '⚠ Please scrape articles first before generating the PDF.';
    return;
  }

  btn.disabled = true;
  status.className = 'export-note';
  status.textContent = '⏳ Generating PDF… this may take a moment.';
  document.getElementById('topbar-status').textContent = 'Generating PDF…';

  try {
    const res = await fetch('/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_name: student })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'PDF generation failed');
    }

    // Trigger download
    const blob     = await res.blob();
    const url      = URL.createObjectURL(blob);
    const link     = document.createElement('a');
    const filename = `Python_Learning_Module_${new Date().toISOString().slice(0,10)}.pdf`;
    link.href = url; link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    status.className = 'export-note success';
    status.textContent = `✓ PDF downloaded: ${filename}`;
    document.getElementById('topbar-status').textContent = 'PDF ready';

  } catch (e) {
    status.className = 'export-note error';
    status.textContent = '⚠ ' + e.message;
    document.getElementById('topbar-status').textContent = 'PDF error';
  }

  btn.disabled = false;
}