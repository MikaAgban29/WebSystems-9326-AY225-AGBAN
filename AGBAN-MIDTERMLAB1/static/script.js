let allGames = [];

function setUrl(url) {
  document.getElementById('url-input').value = url;
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function setProgress(pct, label) {
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-label').textContent = label;
}

async function startScrape() {
  const url = document.getElementById('url-input').value.trim();
  const btn = document.getElementById('scrape-btn');
  const errBox = document.getElementById('error-box');

  if (!url) { showError('Please enter a URL.'); return; }

  errBox.style.display = 'none';
  document.getElementById('results-section').style.display = 'none';
  document.getElementById('game-grid').innerHTML = '';
  btn.disabled = true;
  document.getElementById('btn-icon').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
  document.getElementById('btn-text').textContent = 'Scraping…';
  document.getElementById('progress-wrap').style.display = 'block';
  setProgress(10, 'Connecting to IGN…');

  let prog = 10;
  const progInterval = setInterval(() => {
    prog = Math.min(prog + 2.5, 85);
    const label = prog < 35 ? 'Discovering game pages…'
                : prog < 60 ? 'Fetching game details…'
                : prog < 80 ? 'Extracting metadata…'
                : 'Finalising results…';
    setProgress(prog, label);
  }, 900);

  try {
    const res = await fetch('/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, count: 25 })
    });
    const data = await res.json();
    clearInterval(progInterval);

    if (!res.ok || data.error) {
      showError(data.error || 'Scraping failed. Try a different URL.');
    } else {
      setProgress(100, `Done! ${data.count} games found.`);
      setTimeout(() => {
        document.getElementById('progress-wrap').style.display = 'none';
      }, 1400);
      loadGames(data.games);
    }
  } catch (e) {
    clearInterval(progInterval);
    showError('Server error: ' + e.message);
  }

  btn.disabled = false;
  document.getElementById('btn-icon').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="15" height="15"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
  document.getElementById('btn-text').textContent = 'Scrape';
}

function showError(msg) {
  const box = document.getElementById('error-box');
  document.getElementById('error-text').textContent = msg;
  box.style.display = 'flex';
  document.getElementById('progress-wrap').style.display = 'none';
}

function loadGames(games) {
  allGames = games;

  // Update hero stats
  const platforms = new Set();
  const devs = new Set();
  games.forEach(g => {
    if (g.platform && g.platform !== 'Not Available')
      g.platform.split(/,/).forEach(p => platforms.add(p.trim()));
    if (g.developer && g.developer !== 'Not Available')
      devs.add(g.developer.trim());
  });
  animateCount('stat-games', games.length);
  animateCount('stat-platforms', platforms.size);
  animateCount('stat-devs', devs.size);

  populatePlatformFilter(games);
  document.getElementById('results-section').style.display = 'block';
  document.getElementById('result-count').textContent = games.length;
  renderGames(games);
  document.getElementById('results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  let current = 0;
  const step = Math.max(1, Math.floor(target / 20));
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 40);
}

function populatePlatformFilter(games) {
  const platforms = new Set();
  games.forEach(g => {
    if (g.platform && g.platform !== 'Not Available')
      g.platform.split(/,/).forEach(p => { const c = p.trim(); if (c) platforms.add(c); });
  });
  const sel = document.getElementById('platform-filter');
  sel.innerHTML = '<option value="">All Platforms</option>';
  [...platforms].sort().forEach(p => {
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = p;
    sel.appendChild(opt);
  });
}

function filterGames() {
  const q = document.getElementById('search-input').value.toLowerCase();
  const plat = document.getElementById('platform-filter').value.toLowerCase();
  const filtered = allGames.filter(g => {
    const mQ = !q || [g.title, g.developer, g.publisher, g.platform, g.key_features]
      .some(f => f && f.toLowerCase().includes(q));
    const mP = !plat || (g.platform && g.platform.toLowerCase().includes(plat));
    return mQ && mP;
  });
  document.getElementById('result-count').textContent = filtered.length;
  renderGames(filtered);
}

function renderGames(games) {
  const grid = document.getElementById('game-grid');
  if (!games.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="e-icon">🔍</div>
        <h3>No games found</h3>
        <p>Try adjusting your search or platform filter.</p>
      </div>`;
    return;
  }

  grid.innerHTML = games.map((g, i) => {
    const na = v => (!v || v === 'Not Available') ? null : v;

    const scoreHtml = na(g.score)
      ? `<span class="score-chip">${escHtml(g.score)}</span>`
      : `<span class="score-chip na">No Score</span>`;

    const dateChip = na(g.release_date)
      ? `<span class="chip chip-date">📅 ${escHtml(g.release_date)}</span>` : '';

    const platChips = na(g.platform)
      ? g.platform.split(/,/).slice(0, 3)
          .map(p => `<span class="chip chip-plat">${escHtml(p.trim())}</span>`).join('')
      : '<span class="chip chip-plat" style="opacity:.4">Platform N/A</span>';

    const scraped = g.scraped_at
      ? new Date(g.scraped_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      : '';

    const imageHtml = g.image_url
      ? `<img class="card-image" src="${escHtml(g.image_url)}" alt="${escHtml(g.title)}" loading="lazy"
           onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'card-image-placeholder',textContent:'🎮'}))">`
      : `<div class="card-image-placeholder">🎮</div>`;

    const devVal = na(g.developer)
      ? `<span class="meta-value">${escHtml(g.developer)}</span>`
      : `<span class="meta-value na">N/A</span>`;

    const pubVal = na(g.publisher)
      ? `<span class="meta-value">${escHtml(g.publisher)}</span>`
      : `<span class="meta-value na">N/A</span>`;

    return `
      <div class="game-card" style="animation-delay:${i * 30}ms">
        ${imageHtml}
        <div class="card-body">
          <div class="card-top">
            <div class="game-title">${escHtml(g.title || 'Unknown')}</div>
            ${scoreHtml}
          </div>
          <div class="tag-row">${dateChip}${platChips}</div>
          <div class="features-block">
            <div class="features-label">Summary / Key Features</div>
            <div class="features-text">${escHtml(na(g.key_features) || 'Not available')}</div>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">Developer</span>
              ${devVal}
            </div>
            <div class="meta-item">
              <span class="meta-label">Publisher</span>
              ${pubVal}
            </div>
          </div>
          <div class="card-footer">
            <a class="view-link" href="${escHtml(g.source_url || '#')}" target="_blank" rel="noopener">
              View on IGN
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
            ${scraped ? `<span class="scraped-at">${scraped}</span>` : ''}
          </div>
        </div>
      </div>`;
  }).join('');
}

function setView(mode) {
  document.getElementById('game-grid').classList.toggle('list-view', mode === 'list');
  document.getElementById('grid-btn').classList.toggle('active', mode === 'grid');
  document.getElementById('list-btn').classList.toggle('active', mode === 'list');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('url-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') startScrape();
  });
});