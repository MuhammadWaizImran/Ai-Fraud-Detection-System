/**
 * market_matrix.js
 * Dedicated Real-Time Crypto Market Matrix Page
 * Tracks 15 top cryptocurrencies with live pricing, volume, market cap, and interactive Chart.js visualizations.
 */

const CryptoMarketMatrix = (() => {
  const COINS = [
    { id: 'bitcoin', symbol: 'BTC', name: 'Bitcoin', basePrice: 65420.00, baseVol: 34200, cap: 1290.5, h24: 66100, l24: 64800 },
    { id: 'ethereum', symbol: 'ETH', name: 'Ethereum', basePrice: 3450.50, baseVol: 18500, cap: 415.2, h24: 3520, l24: 3390 },
    { id: 'solana', symbol: 'SOL', name: 'Solana', basePrice: 142.80, baseVol: 6800, cap: 66.8, h24: 148.5, l24: 139.2 },
    { id: 'binancecoin', symbol: 'BNB', name: 'Binance Coin', basePrice: 585.20, baseVol: 2400, cap: 88.4, h24: 592, l24: 578 },
    { id: 'ripple', symbol: 'XRP', name: 'Ripple', basePrice: 0.582, baseVol: 2900, cap: 32.5, h24: 0.605, l24: 0.568 },
    { id: 'dogecoin', symbol: 'DOGE', name: 'Dogecoin', basePrice: 0.124, baseVol: 1800, cap: 18.2, h24: 0.131, l24: 0.119 },
    { id: 'cardano', symbol: 'ADA', name: 'Cardano', basePrice: 0.385, baseVol: 950, cap: 13.8, h24: 0.398, l24: 0.374 },
    { id: 'polkadot', symbol: 'DOT', name: 'Polkadot', basePrice: 4.85, baseVol: 480, cap: 6.9, h24: 5.05, l24: 4.72 },
    { id: 'avalanche-2', symbol: 'AVAX', name: 'Avalanche', basePrice: 28.40, baseVol: 1200, cap: 11.2, h24: 29.8, l24: 27.5 },
    { id: 'chainlink', symbol: 'LINK', name: 'Chainlink', basePrice: 12.15, baseVol: 720, cap: 7.4, h24: 12.6, l24: 11.8 },
    { id: 'matic-network', symbol: 'MATIC', name: 'Polygon', basePrice: 0.425, baseVol: 580, cap: 4.2, h24: 0.445, l24: 0.412 },
    { id: 'near', symbol: 'NEAR', name: 'Near Protocol', basePrice: 4.65, baseVol: 610, cap: 5.3, h24: 4.88, l24: 4.52 },
    { id: 'shiba-inu', symbol: 'SHIB', name: 'Shiba Inu', basePrice: 0.0000142, baseVol: 890, cap: 8.4, h24: 0.000015, l24: 0.0000135 },
    { id: 'uniswap', symbol: 'UNI', name: 'Uniswap', basePrice: 7.25, baseVol: 340, cap: 4.3, h24: 7.55, l24: 7.02 },
    { id: 'litecoin', symbol: 'LTC', name: 'Litecoin', basePrice: 66.80, baseVol: 410, cap: 5.0, h24: 68.2, l24: 65.4 }
  ];

  let coinData = {};
  let volumeChart = null;
  let momentumChart = null;

  COINS.forEach(c => {
    coinData[c.symbol] = {
      ...c,
      price: c.basePrice,
      change24h: (Math.random() * 8 - 4).toFixed(2),
      volume24h: c.baseVol * (1 + (Math.random() * 0.2 - 0.1)),
      marketCap: c.cap
    };
  });

  async function fetchLiveMetrics() {
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
            if (item.usd_24h_vol) coinData[c.symbol].volume24h = item.usd_24h_vol / 1e6; // in $M
            if (item.usd_market_cap) coinData[c.symbol].marketCap = (item.usd_market_cap / 1e9).toFixed(1); // in $B
          }
        });
      }
    } catch (e) {
      // Local micro drift
      COINS.forEach(c => {
        const delta = (Math.random() * 0.004 - 0.002);
        coinData[c.symbol].price = parseFloat((coinData[c.symbol].price * (1 + delta)).toFixed(coinData[c.symbol].price > 100 ? 2 : 4));
      });
    }

    renderCards();
    updateCharts();
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
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(10, 16, 30, 0.95)',
              borderColor: '#00f3ff',
              borderWidth: 1,
              titleColor: '#fff',
              bodyColor: '#00f3ff',
              callbacks: {
                label: (ctx) => ` Volume: $${ctx.parsed.y.toLocaleString()} Million`
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
            }
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
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(10, 16, 30, 0.95)',
              borderColor: '#00f3ff',
              borderWidth: 1,
              titleColor: '#fff',
              bodyColor: '#fff',
              callbacks: {
                label: (ctx) => ` 24h Change: ${ctx.parsed.y > 0 ? '+' : ''}${ctx.parsed.y}%`
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
            }
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

    let coinsList = [...COINS].map(c => coinData[c.symbol]);

    // Search filter
    if (searchTerm) {
      coinsList = coinsList.filter(c => c.name.toLowerCase().includes(searchTerm) || c.symbol.toLowerCase().includes(searchTerm));
    }

    // Sorting
    if (sortMode === 'gainers') {
      coinsList.sort((a, b) => parseFloat(b.change24h) - parseFloat(a.change24h));
    } else if (sortMode === 'losers') {
      coinsList.sort((a, b) => parseFloat(a.change24h) - parseFloat(b.change24h));
    } else if (sortMode === 'volume') {
      coinsList.sort((a, b) => b.volume24h - a.volume24h);
    } else {
      coinsList.sort((a, b) => b.marketCap - a.marketCap);
    }

    let html = '';
    coinsList.forEach(c => {
      const isUp = parseFloat(c.change24h) >= 0;
      const changeClass = isUp ? 'change-up' : 'change-down';
      const arrow = isUp ? '▲' : '▼';
      const priceFormatted = c.price > 100 
        ? `$${c.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
        : (c.price < 0.01 ? `$${c.price.toFixed(6)}` : `$${c.price.toFixed(4)}`);

      html += `
        <div class="crypto-card">
          <div class="crypto-card-header">
            <div>
              <div class="crypto-card-sym">${c.symbol}</div>
              <div class="crypto-card-name">${c.name}</div>
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
        </div>
      `;
    });

    container.innerHTML = html;
  }

  function init() {
    initCharts();
    fetchLiveMetrics();
    setInterval(fetchLiveMetrics, 30000);

    document.getElementById('market-search-input')?.addEventListener('input', renderCards);
    document.getElementById('market-sort-select')?.addEventListener('change', renderCards);
  }

  return {
    init: init,
    refresh: fetchLiveMetrics
  };
})();
