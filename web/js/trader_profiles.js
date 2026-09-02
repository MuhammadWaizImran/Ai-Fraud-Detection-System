/**
 * trader_profiles.js
 * Searchable & Filterable Monitored Trader Entity Directory
 * Displays Trader Risk Tier Badges, violation counts, and primary attack patterns.
 */

const TraderProfiles = (() => {
  const TRADERS_DATA = [];
  const KNOWN_FLAGGED = ['TRADER_0012', 'TRADER_0042', 'TRADER_0068', 'TRADER_0077', 'TRADER_0099', 'TRADER_0103', 'TRADER_0155', 'TRADER_0169'];
  const KNOWN_WATCH = ['TRADER_0018', 'TRADER_0028', 'TRADER_0036', 'TRADER_0055', 'TRADER_0080', 'TRADER_0114', 'TRADER_0146', 'TRADER_0172'];

  for (let i = 1; i <= 60; i++) {
    const tid = `TRADER_${String(i).padStart(4, '0')}`;
    let tier = 'NORMAL';
    let riskScore = (Math.random() * 0.35 + 0.05).toFixed(4);
    let violations = Math.floor(Math.random() * 3);
    let primaryAttack = 'None';
    let totalVol = (Math.random() * 500 + 50).toFixed(1);

    if (KNOWN_FLAGGED.includes(tid) || Math.random() < 0.12) {
      tier = 'FLAGGED';
      riskScore = (Math.random() * 0.12 + 0.88).toFixed(4);
      violations = Math.floor(Math.random() * 25 + 12);
      const attacks = ['Wash Trading', 'Spoofing', 'Layering', 'Volume Spike (Pump & Dump)'];
      primaryAttack = attacks[Math.floor(Math.random() * attacks.length)];
      totalVol = (Math.random() * 3500 + 1200).toFixed(1);
    } else if (KNOWN_WATCH.includes(tid) || Math.random() < 0.18) {
      tier = 'WATCH';
      riskScore = (Math.random() * 0.25 + 0.55).toFixed(4);
      violations = Math.floor(Math.random() * 8 + 3);
      primaryAttack = 'High Cancel Velocity';
      totalVol = (Math.random() * 1200 + 400).toFixed(1);
    }

    TRADERS_DATA.push({
      id: tid,
      tier: tier,
      riskScore: riskScore,
      violations: violations,
      primaryAttack: primaryAttack,
      totalVolume: totalVol,
      favAsset: ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE'][Math.floor(Math.random() * 5)]
    });
  }

  function renderGrid() {
    const container = document.getElementById('trader-cards-grid');
    if (!container) return;

    const searchTerm = (document.getElementById('trader-search-input')?.value || '').toLowerCase().trim();
    const activeTierBtn = document.querySelector('.tier-btn.active');
    const filterTier = activeTierBtn ? activeTierBtn.getAttribute('data-tier') : 'ALL';

    let list = [...TRADERS_DATA];

    if (filterTier !== 'ALL') {
      list = list.filter(t => t.tier === filterTier);
    }

    if (searchTerm) {
      list = list.filter(t => t.id.toLowerCase().includes(searchTerm) || t.primaryAttack.toLowerCase().includes(searchTerm));
    }

    let html = '';
    list.forEach(t => {
      let badgeClass = 'pill-safe';
      let badgeText = 'NORMAL (LOW)';
      if (t.tier === 'FLAGGED') {
        badgeClass = 'pill-fraud';
        badgeText = '🚨 FLAGGED (HIGH)';
      } else if (t.tier === 'WATCH') {
        badgeClass = 'pill-suspicious';
        badgeText = '⚠️ WATCHLIST';
      }

      html += `
        <div class="trader-card ${t.tier === 'FLAGGED' ? 'trader-card-flagged' : ''}">
          <div class="trader-card-header">
            <div>
              <div class="trader-card-id">${t.id}</div>
              <div style="font-size:11px;color:var(--text-dim);">Fav Market: <span style="color:var(--cyan);font-weight:700;">${t.favAsset}</span></div>
            </div>
            <span class="pill ${badgeClass}">${badgeText}</span>
          </div>

          <div style="margin: 14px 0; font-family:var(--font-mono);">
            <div style="font-size:11px;color:var(--text-muted);">Risk Metric Score:</div>
            <div style="font-size:22px;font-weight:900;color:${t.tier === 'FLAGGED' ? 'var(--red)' : (t.tier === 'WATCH' ? 'var(--amber)' : 'var(--emerald)')};">
              ${t.riskScore}
            </div>
          </div>

          <div class="crypto-card-metrics">
            <div class="crypto-metric-row">
              <span>Total Violations:</span>
              <strong style="color:${t.violations > 5 ? 'var(--red)' : '#fff'};">${t.violations} Interceptions</strong>
            </div>
            <div class="crypto-metric-row">
              <span>Primary Modality:</span>
              <span style="color:var(--text-main);font-size:11px;">${t.primaryAttack}</span>
            </div>
            <div class="crypto-metric-row">
              <span>Session Volume:</span>
              <strong style="color:var(--cyan);">$${parseFloat(t.totalVolume).toLocaleString()}K</strong>
            </div>
          </div>

          <button onclick="TraderProfiles.inspectTrader('${t.id}')" class="btn-cyber" style="width:100%;margin-top:12px;justify-content:center;font-size:11px;padding:6px 0;">
            🔍 INVESTIGATE IN COPILOT
          </button>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  function inspectTrader(traderId) {
    const trader = TRADERS_DATA.find(t => t.id === traderId);
    if (!trader) return;

    // Open Copilot Chatbot
    const trigger = document.getElementById('copilot-trigger');
    const drawer = document.getElementById('copilot-drawer');
    if (drawer && !drawer.classList.contains('active')) {
      trigger.click();
    }

    const messages = document.getElementById('copilot-messages');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble bubble-ai';
    bubble.innerHTML = `
      <div style="font-size:14px;font-weight:800;color:var(--cyan);margin-bottom:6px;">👤 Regulatory Trader Audit: \`${trader.id}\`</div>
      * **Entity Risk Tier:** <strong>[${trader.tier}]</strong> | **Score:** \`${trader.riskScore}\`<br/>
      * **Historical Violations:** <strong>${trader.violations} Fraud Interceptions</strong><br/>
      * **Primary Modality:** \`${trader.primaryAttack}\`<br/>
      * **Traded Session Volume:** \`$${parseFloat(trader.totalVolume).toLocaleString()}K\`<br/><br/>
      ${trader.tier === 'FLAGGED' ? '🚨 **Compliance Warning:** High concentration of wash trading and order book spoofing. Entity is automatically flagged in Gold Delta Lakehouse for compliance audit.' : '🟢 **Status:** Normal institutional liquidity provider profile with compliant microstructural flow.'}
    `;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  function init() {
    renderGrid();
    document.getElementById('trader-search-input')?.addEventListener('input', renderGrid);

    document.querySelectorAll('.tier-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderGrid();
      });
    });
  }

  return {
    init: init,
    inspectTrader: inspectTrader
  };
})();
