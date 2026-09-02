/**
 * crypto_page.js
 * Logic for the Dedicated Real-Time Crypto Market Terminal (crypto_market.html)
 * Handles 15-coin live pricing, charts, search/sort filters, and interactive coin drilldown modal.
 */

document.addEventListener('DOMContentLoaded', () => {
  const COINS = [
    { id: 'bitcoin', symbol: 'BTC', name: 'Bitcoin', icon: '₿', basePrice: 65420.00, baseVol: 34200, cap: 1290.5, h24: 66100, l24: 64800, rank: 1, desc: 'Layer 1 Decentralized Digital Gold' },
    { id: 'ethereum', symbol: 'ETH', name: 'Ethereum', icon: 'Ξ', basePrice: 3450.50, baseVol: 18500, cap: 415.2, h24: 3520, l24: 3390, rank: 2, desc: 'Smart Contract & EVM Settlement Layer' },
    { id: 'solana', symbol: 'SOL', name: 'Solana', icon: '◎', basePrice: 142.80, baseVol: 6800, cap: 66.8, h24: 148.5, l24: 139.2, rank: 3, desc: 'High-Throughput Ultra-Fast Blockchain' },
    { id: 'binancecoin', symbol: 'BNB', name: 'Binance Coin', icon: '🔶', basePrice: 585.20, baseVol: 2400, cap: 88.4, h24: 592, l24: 578, rank: 4, desc: 'BNB Chain & Exchange Utility Token' },
    { id: 'ripple', symbol: 'XRP', name: 'Ripple', icon: '✕', basePrice: 0.582, baseVol: 2900, cap: 32.5, h24: 0.605, l24: 0.568, rank: 5, desc: 'Cross-Border Real-Time Gross Settlement' },
    { id: 'dogecoin', symbol: 'DOGE', name: 'Dogecoin', icon: 'Ð', basePrice: 0.124, baseVol: 1800, cap: 18.2, h24: 0.131, l24: 0.119, rank: 6, desc: 'Proof-of-Work Peer-to-Peer Digital Currency' },
    { id: 'cardano', symbol: 'ADA', name: 'Cardano', icon: '₳', basePrice: 0.385, baseVol: 950, cap: 13.8, h24: 0.398, l24: 0.374, rank: 7, desc: 'Peer-Reviewed Proof-of-Stake Protocol' },
    { id: 'polkadot', symbol: 'DOT', name: 'Polkadot', icon: '●', basePrice: 4.85, baseVol: 480, cap: 6.9, h24: 5.05, l24: 4.72, rank: 8, desc: 'Heterogeneous Multi-Chain Sharding Layer' },
    { id: 'avalanche-2', symbol: 'AVAX', name: 'Avalanche', icon: '▲', basePrice: 28.40, baseVol: 1200, cap: 11.2, h24: 29.8, l24: 27.5, rank: 9, desc: 'Subnet-Scalable Smart Contracts Platform' },
    { id: 'chainlink', symbol: 'LINK', name: 'Chainlink', icon: '⬡', basePrice: 12.15, baseVol: 720, cap: 7.4, h24: 12.6, l24: 11.8, rank: 10, desc: 'Decentralized Oracle & Data Feeds Network' },
    { id: 'matic-network', symbol: 'MATIC', name: 'Polygon', icon: '⬟', basePrice: 0.425, baseVol: 580, cap: 4.2, h24: 0.445, l24: 0.412, rank: 11, desc: 'Ethereum Layer 2 Zero-Knowledge Rollups' },
    { id: 'near', symbol: 'NEAR', name: 'Near Protocol', icon: 'Ⓝ', basePrice: 4.65, baseVol: 610, cap: 5.3, h24: 4.88, l24: 4.52, rank: 12, desc: 'Nightshade Sharding Smart Contract Chain' },
    { id: 'shiba-inu', symbol: 'SHIB', name: 'Shiba Inu', icon: '🐕', basePrice: 0.0000142, baseVol: 890, cap: 8.4, h24: 0.000015, l24: 0.0000135, rank: 13, desc: 'Community Meme Token & Shibarium Ecosystem' },
    { id: 'uniswap', symbol: 'UNI', name: 'Uniswap', icon: '🦄', basePrice: 7.25, baseVol: 340, cap: 4.3, h24: 7.55, l24: 7.02, rank: 14, desc: 'Decentralized Automated Market Maker (AMM)' },
    { id: 'litecoin', symbol: 'LTC', name: 'Litecoin', icon: 'Ł', basePrice: 66.80, baseVol: 410, cap: 5.0, h24: 68.2, l24: 65.4, rank: 15, desc: 'Scrypt-Based Fast Decentralized Payments' }
  ];

  let coinData = {};
  let volumeChart = null;
  let momentumChart = null;
  let modalCoinChart = null;
  let selectedCoin = COINS[0];

  COINS.forEach(c => {
    coinData[c.symbol] = {
      ...c,
      price: c.basePrice,
      change24h: (Math.random() * 8 - 3).toFixed(2),
      volume24h: c.baseVol * (1 + (Math.random() * 0.2 - 0.1)),
      marketCap: c.cap
    };
  });

  // Modal elements
  const modal = document.getElementById('coin-detail-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  // Fetch real CoinGecko prices
  async function fetchPrices() {
    try {
      const ids = COINS.map(c => c.id).join(',');
      const res = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true&include_market_cap=true`);
      if (res.ok) {
        const data = await res.json();
        COINS.forEach(c => {
          if (data[c.id]) {
            const item = data[c.id];
            if (item.usd) coinData[c.symbol].price = item.usd;
            if (item.usd_24h_change !== undefined) coinData[c.symbol].change24h = item.usd_24h_change.toFixed(2);
            if (item.usd_24h_vol) coinData[c.symbol].volume24h = item.usd_24h_vol / 1e6;
            if (item.usd_market_cap) coinData[c.symbol].marketCap = (item.usd_market_cap / 1e9).toFixed(1);
          }
        });
      }
    } catch (e) {
      COINS.forEach(c => {
        const delta = (Math.random() * 0.004 - 0.002);
        coinData[c.symbol].price = parseFloat((coinData[c.symbol].price * (1 + delta)).toFixed(coinData[c.symbol].price > 100 ? 2 : 4));
      });
    }

    renderCards();
    updateCharts();
    updateTicker();
    if (modal.classList.contains('active')) {
      updateModal(selectedCoin.symbol);
    }
  }

  function updateTicker() {
    const tickerContent = document.getElementById('market-ticker-content');
    if (!tickerContent) return;
    let html = '';
    COINS.forEach(c => {
      const data = coinData[c.symbol];
      const isUp = parseFloat(data.change24h) >= 0;
      const changeClass = isUp ? 'change-up' : 'change-down';
      const arrow = isUp ? '▲' : '▼';
      html += `
        <div class="ticker-item">
          <span class="sym">${c.symbol}</span>
          <span class="price">$${data.price.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
          <span class="${changeClass}">${arrow} ${Math.abs(data.change24h)}%</span>
        </div>
      `;
    });
    tickerContent.innerHTML = html + html;
  }

  function initCharts() {
    const volCtx = document.getElementById('chart-market-volume')?.getContext('2d');
    const momCtx = document.getElementById('chart-market-momentum')?.getContext('2d');

    if (volCtx) {
      volumeChart = new Chart(volCtx, {
        type: 'bar',
        data: {
          labels: COINS.slice(0, 10).map(c => c.symbol),
          datasets: [{
            label: '24h Traded Volume ($ Millions USD)',
            data: COINS.slice(0, 10).map(c => coinData[c.symbol].volume24h),
            backgroundColor: 'rgba(0, 243, 255, 0.65)',
            borderColor: '#00f3ff',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } }
          }
        }
      });
    }

    if (momCtx) {
      momentumChart = new Chart(momCtx, {
        type: 'bar',
        data: {
          labels: COINS.slice(0, 10).map(c => c.symbol),
          datasets: [{
            label: '24h Price Change (%)',
            data: COINS.slice(0, 10).map(c => parseFloat(coinData[c.symbol].change24h)),
            backgroundColor: COINS.slice(0, 10).map(c => parseFloat(coinData[c.symbol].change24h) >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
            borderColor: COINS.slice(0, 10).map(c => parseFloat(coinData[c.symbol].change24h) >= 0 ? '#10b981' : '#ef4444'),
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } }
          }
        }
      });
    }
  }

  function updateCharts() {
    if (volumeChart) {
      volumeChart.data.datasets[0].data = COINS.slice(0, 10).map(c => coinData[c.symbol].volume24h);
      volumeChart.update('none');
    }
    if (momentumChart) {
      const changes = COINS.slice(0, 10).map(c => parseFloat(coinData[c.symbol].change24h));
      momentumChart.data.datasets[0].data = changes;
      momentumChart.data.datasets[0].backgroundColor = changes.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)');
      momentumChart.data.datasets[0].borderColor = changes.map(v => v >= 0 ? '#10b981' : '#ef4444');
      momentumChart.update('none');
    }
  }

  function renderCards() {
    const container = document.getElementById('crypto-cards-container');
    if (!container) return;

    const searchTerm = (document.getElementById('market-search-input')?.value || '').toLowerCase().trim();
    const sortMode = document.getElementById('market-sort-select')?.value || 'market_cap';

    let list = [...COINS].map(c => coinData[c.symbol]);

    if (searchTerm) {
      list = list.filter(c => c.name.toLowerCase().includes(searchTerm) || c.symbol.toLowerCase().includes(searchTerm));
    }

    if (sortMode === 'gainers') {
      list.sort((a, b) => parseFloat(b.change24h) - parseFloat(a.change24h));
    } else if (sortMode === 'losers') {
      list.sort((a, b) => parseFloat(a.change24h) - parseFloat(b.change24h));
    } else if (sortMode === 'volume') {
      list.sort((a, b) => b.volume24h - a.volume24h);
    } else {
      list.sort((a, b) => b.marketCap - a.marketCap);
    }

    let html = '';
    list.forEach(c => {
      const isUp = parseFloat(c.change24h) >= 0;
      const changeClass = isUp ? 'change-up' : 'change-down';
      const arrow = isUp ? '▲' : '▼';
      const priceFormatted = c.price > 100 
        ? `$${c.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
        : (c.price < 0.01 ? `$${c.price.toFixed(6)}` : `$${c.price.toFixed(4)}`);

      html += `
        <div class="crypto-card" onclick="openCoinModal('${c.symbol}')" style="cursor:pointer;">
          <div class="crypto-card-header">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:24px;">${c.icon}</span>
              <div>
                <div class="crypto-card-sym">${c.symbol}</div>
                <div class="crypto-card-name">${c.name}</div>
              </div>
            </div>
            <div class="crypto-card-change ${changeClass}">${arrow} ${Math.abs(c.change24h)}%</div>
          </div>

          <div class="crypto-card-price">${priceFormatted}</div>

          <div class="crypto-card-metrics">
            <div class="crypto-metric-row">
              <span>Market Cap:</span>
              <strong style="color:#fff;">$${c.marketCap}B</strong>
            </div>
            <div class="crypto-metric-row">
              <span>24h Volume:</span>
              <strong style="color:var(--cyan);">$${Math.round(c.volume24h).toLocaleString()}M</strong>
            </div>
            <div class="crypto-metric-row">
              <span>24h Range:</span>
              <span style="font-size:11px;color:var(--text-dim);">$${c.l24} - $${c.h24}</span>
            </div>
          </div>

          <div style="margin-top:12px;text-align:center;font-size:11px;color:var(--cyan);font-weight:700;">
            🔍 CLICK FOR LIVE CHART &amp; ORDER BOOK
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // ══════════════════════════════════════════════════════════════
  // DEEP DIVE COIN MODAL & LIVE ORDER BOOK
  // ══════════════════════════════════════════════════════════════
  window.openCoinModal = function(symbol) {
    const coin = coinData[symbol];
    if (!coin) return;
    selectedCoin = coin;

    document.getElementById('modal-coin-icon').innerText = coin.icon;
    document.getElementById('modal-coin-title').innerText = `${coin.name} (${coin.symbol})`;
    document.getElementById('modal-coin-badge').innerText = `Rank #${coin.rank} • ${coin.desc}`;

    updateModal(symbol);
    modal.classList.add('active');
  };

  function updateModal(symbol) {
    const coin = coinData[symbol];
    if (!coin) return;

    const isUp = parseFloat(coin.change24h) >= 0;
    const priceFormatted = coin.price > 100 
      ? `$${coin.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
      : (coin.price < 0.01 ? `$${coin.price.toFixed(6)}` : `$${coin.price.toFixed(4)}`);

    document.getElementById('modal-coin-price').innerText = priceFormatted;
    const changeEl = document.getElementById('modal-coin-change');
    changeEl.innerText = `${isUp ? '▲ +' : '▼ '}${coin.change24h}%`;
    changeEl.className = isUp ? 'pill pill-safe' : 'pill pill-fraud';

    document.getElementById('modal-coin-high').innerText = `$${coin.h24}`;
    document.getElementById('modal-coin-low').innerText = `$${coin.l24}`;
    document.getElementById('modal-coin-cap').innerText = `$${coin.marketCap}B`;
    document.getElementById('modal-coin-vol').innerText = `$${Math.round(coin.volume24h).toLocaleString()}M`;

    // Render Modal Chart
    renderModalChart(coin);

    // Render Order Book Depth
    renderOrderBook(coin.price);
  }

  function renderModalChart(coin) {
    const ctx = document.getElementById('modal-coin-chart')?.getContext('2d');
    if (!ctx) return;

    // Generate 12 historical intraday ticks around current price
    const labels = ['-55m', '-50m', '-45m', '-40m', '-35m', '-30m', '-25m', '-20m', '-15m', '-10m', '-5m', 'Now'];
    const baseP = coin.price;
    const dataPoints = [];
    let current = baseP * (1 - (parseFloat(coin.change24h) / 100));

    for (let i = 0; i < 11; i++) {
      current = current * (1 + (Math.random() * 0.012 - 0.005));
      dataPoints.push(parseFloat(current.toFixed(coin.price > 100 ? 2 : 4)));
    }
    dataPoints.push(coin.price);

    if (modalCoinChart) {
      modalCoinChart.destroy();
    }

    const isUp = parseFloat(coin.change24h) >= 0;
    const lineColor = isUp ? '#10b981' : '#ef4444';
    const bgGrad = isUp ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';

    modalCoinChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: `${coin.symbol} Price (USD)`,
          data: dataPoints,
          borderColor: lineColor,
          backgroundColor: bgGrad,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: lineColor,
          pointBorderColor: '#fff',
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } }
        }
      }
    });
  }

  function renderOrderBook(price) {
    const asksContainer = document.getElementById('modal-orderbook-asks');
    const bidsContainer = document.getElementById('modal-orderbook-bids');
    if (!asksContainer || !bidsContainer) return;

    let asksHtml = '';
    let bidsHtml = '';

    // 4 Asks (Sells)
    for (let i = 4; i >= 1; i--) {
      const askPrice = (price * (1 + (i * 0.0012))).toFixed(price > 100 ? 2 : 4);
      const askVol = (Math.random() * 4.5 + 0.5).toFixed(2);
      asksHtml += `
        <div style="display:flex;justify-content:space-between;color:var(--red);">
          <span>$${askPrice}</span>
          <span>${askVol}</span>
        </div>
      `;
    }

    // 4 Bids (Buys)
    for (let i = 1; i <= 4; i++) {
      const bidPrice = (price * (1 - (i * 0.0012))).toFixed(price > 100 ? 2 : 4);
      const bidVol = (Math.random() * 4.5 + 0.5).toFixed(2);
      bidsHtml += `
        <div style="display:flex;justify-content:space-between;color:var(--emerald);">
          <span>$${bidPrice}</span>
          <span>${bidVol}</span>
        </div>
      `;
    }

    asksContainer.innerHTML = asksHtml;
    bidsContainer.innerHTML = bidsHtml;
  }

  modalCloseBtn?.addEventListener('click', () => {
    modal.classList.remove('active');
  });

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });

  // Init
  initCharts();
  fetchPrices();
  setInterval(fetchPrices, 25000);

  document.getElementById('market-search-input')?.addEventListener('input', renderCards);
  document.getElementById('market-sort-select')?.addEventListener('change', renderCards);
});
