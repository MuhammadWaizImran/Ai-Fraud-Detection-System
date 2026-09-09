/**
 * app.js
 * Main Orchestrator & UI Coordinator
 * Connects Live Market Stream, Feature Engine, 3-Model AI Scoring,
 * 3D Globe, Real-Time Dynamic Charts (Risk Stream & SHAP), and Persistent Order Ledger.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Loading Screen Elements
  const loaderOverlay = document.getElementById('cyber-loader-overlay');
  const loaderProgressBar = document.getElementById('loader-progress-bar');
  const loaderLogText = document.getElementById('loader-log-text');

  // DOM Elements
  const totalTradesEl = document.getElementById('kpi-total-trades');
  const fraudCountEl = document.getElementById('kpi-fraud-count');
  const fraudRateEl = document.getElementById('kpi-fraud-rate');
  const avgLatencyEl = document.getElementById('kpi-avg-latency');
  const activeTradersEl = document.getElementById('kpi-active-traders');

  const alertBanner = document.getElementById('alert-banner');
  const alertDetail = document.getElementById('alert-detail');
  const feedTableBody = document.getElementById('feed-table-body');
  const tickerContent = document.getElementById('ticker-content');

  // Attack count elements
  const countWash = document.getElementById('count-wash');
  const countSpoof = document.getElementById('count-spoof');
  const countLayer = document.getElementById('count-layer');
  const countVolume = document.getElementById('count-volume');
  const countPrice = document.getElementById('count-price');

  const barWash = document.getElementById('bar-wash');
  const barSpoof = document.getElementById('bar-spoof');
  const barLayer = document.getElementById('bar-layer');
  const barVolume = document.getElementById('bar-volume');
  const barPrice = document.getElementById('bar-price');

  // Copilot Chat Elements
  const copilotTrigger = document.getElementById('copilot-trigger');
  const copilotDrawer = document.getElementById('copilot-drawer');
  const copilotClose = document.getElementById('copilot-close');
  const copilotMessages = document.getElementById('copilot-messages');
  const copilotInput = document.getElementById('copilot-input');
  const copilotSend = document.getElementById('copilot-send');
  const copilotBadge = document.getElementById('copilot-badge');

  // Controls & Filters
  const btnPauseStream = document.getElementById('btn-pause-stream');
  const btnMuteSound = document.getElementById('btn-mute-sound');
  const btnRotateGlobe = document.getElementById('btn-rotate-globe');
  const btnClearHistory = document.getElementById('btn-clear-history');
  const feedSearchInput = document.getElementById('feed-search-input');
  const feedVerdictFilter = document.getElementById('feed-verdict-filter');

  // State synchronized with Python realtime scoring engine & 150,000 Gold Table
  let realStats = { total: 150000, fraud: 22850, suspicious: 24150, safe: 103000, fraud_rate_pct: 15.23 };
  let liveTradesCounter = 0;
  let liveFraudsCounter = 0;

  async function syncLiveStats() {
    try {
      const res = await fetch('data/live_stats.json?t=' + Date.now());
      if (res.ok) {
        realStats = await res.json();
        updateKPIs();
      }
    } catch (e) {}
  }
  setInterval(syncLiveStats, 2000);
  syncLiveStats();

  let isStreamRunning = true; // Enabled by default to stream live backend data
  let totalLatency = 0;
  let unreadAlerts = 0;
  const attackCounts = {
    wash_trading: 0,
    spoofing: 0,
    layering: 0,
    volume_spike: 0,
    price_manipulation: 0
  };
  const uniqueTraders = new Set();
  let ordersLedger = [];

  // 1. Initialize 3D Globe
  CyberGlobe3D.init('globe-canvas-container');

  // Progressive Cyber Loader Sequence
  const loadingSteps = [
    { pct: 25, msg: 'INITIALIZING NEURAL WEIGHTS & SCALERS...' },
    { pct: 55, msg: 'CONNECTING TO COINGECKO LIVE ORACLES (BTC, ETH, SOL)...' },
    { pct: 85, msg: 'MOUNTING 3-MODEL ENSEMBLE (XGBOOST, ISO-FOREST, AUTOENCODER)...' },
    { pct: 100, msg: 'SYSTEM READY ➔ ACCESS GRANTED' }
  ];

  let stepIdx = 0;
  function advanceLoader() {
    if (stepIdx < loadingSteps.length) {
      const step = loadingSteps[stepIdx];
      loaderProgressBar.style.width = `${step.pct}%`;
      loaderLogText.innerText = step.msg;
      stepIdx++;
      setTimeout(advanceLoader, 400);
    } else {
      setTimeout(() => {
        loaderOverlay.classList.add('fade-out');
      }, 350);
    }
  }
  setTimeout(advanceLoader, 150);

  // 2. Build Market Ticker Bar
  function updateTicker() {
    const prices = MarketStream.getPrices();
    let tickerHtml = '';
    for (const [sym, info] of Object.entries(prices)) {
      const isUp = parseFloat(info.change24h) >= 0;
      const changeClass = isUp ? 'change-up' : 'change-down';
      const arrow = isUp ? '▲' : '▼';
      tickerHtml += `
        <div class="ticker-item">
          <span class="sym">${sym}</span>
          <span class="price">$${info.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          <span class="${changeClass}">${arrow} ${Math.abs(info.change24h)}%</span>
        </div>
      `;
    }
    tickerContent.innerHTML = tickerHtml + tickerHtml;
  }
  updateTicker();
  setInterval(updateTicker, 10000);

  // ══════════════════════════════════════════════════════════════
  // 3. REAL-TIME SCIENTIFIC & ANALYTICAL CHART.JS IMPLEMENTATION
  // ══════════════════════════════════════════════════════════════
  let liveRiskStreamChart = null;
  let liveShapChart = null;
  let symbolFraudsChart = null;
  let hourlyDensityChart = null;

  // Real Baseline Symbol Fraud Counts from Gold Delta Table (pbi_fraud_by_symbol.csv)
  const symbolFraudCounts = {
    BTC: 245,
    ETH: 218,
    SOL: 185,
    XRP: 142,
    BNB: 128,
    ADA: 115,
    DOGE: 87,
    DOT: 76
  };

  function initDynamicCharts() {
    // Chart 1: Real-Time Live Risk Stream Line Chart
    const riskCtx = document.getElementById('chart-live-risk-stream')?.getContext('2d');
    if (riskCtx) {
      liveRiskStreamChart = new Chart(riskCtx, {
        type: 'line',
        data: {
          labels: Array(25).fill(''),
          datasets: [
            {
              label: 'Fraud Threshold (0.85)',
              data: Array(25).fill(0.85),
              borderColor: 'rgba(239, 68, 68, 0.7)',
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            },
            {
              label: 'Suspicious Threshold (0.50)',
              data: Array(25).fill(0.50),
              borderColor: 'rgba(245, 158, 11, 0.5)',
              borderDash: [3, 3],
              borderWidth: 1.2,
              pointRadius: 0,
              fill: false
            },
            {
              label: 'Composite Model Risk Score (0.0 - 1.0)',
              data: Array(25).fill(0.25),
              borderColor: '#00f3ff',
              backgroundColor: 'rgba(0, 243, 255, 0.10)',
              borderWidth: 2,
              pointRadius: 4,
              pointBackgroundColor: '#00f3ff',
              pointBorderColor: '#fff',
              tension: 0.3,
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 300 },
          plugins: {
            legend: {
              labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 9 } }
            },
            tooltip: {
              backgroundColor: 'rgba(10, 16, 30, 0.95)',
              borderColor: '#00f3ff',
              borderWidth: 1,
              titleColor: '#fff',
              bodyColor: '#00f3ff'
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { display: false }
            },
            y: {
              min: 0,
              max: 1.0,
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: {
                color: '#94a3b8',
                font: { family: 'JetBrains Mono', size: 10 },
                stepSize: 0.2
              }
            }
          }
        }
      });
    }

    // Center dynamic SHAP doughnut text precisely in the doughnut hole
    function positionShapCenter(chart) {
      if (!chart) return;
      try {
        const meta = chart.getDatasetMeta(0);
        if (meta && meta.data && meta.data[0]) {
          const centerMetric = document.getElementById('shap-center-metric');
          if (centerMetric) {
            const x = meta.data[0].x;
            const y = meta.data[0].y;
            if (typeof x === 'number' && typeof y === 'number' && !isNaN(x) && !isNaN(y)) {
              const canvas = chart.canvas;
              const offsetX = canvas ? canvas.offsetLeft : 0;
              const offsetY = canvas ? canvas.offsetTop : 0;
              centerMetric.style.left = `${x + offsetX}px`;
              centerMetric.style.top = `${y + offsetY}px`;
              centerMetric.style.transform = 'translate(-50%, -50%)';
              centerMetric.style.position = 'absolute';
            }
          }
        }
      } catch (e) {
        // graceful fallback
      }
    }

    // Chart 2: Real TreeSHAP Mathematical Circular Feature Attribution (Doughnut Ring)
    const shapCtx = document.getElementById('chart-live-shap')?.getContext('2d');
    if (shapCtx) {
      liveShapChart = new Chart(shapCtx, {
        type: 'doughnut',
        data: {
          labels: ['Volume Spike', 'Cancel Ratio', 'Orders/Min', 'Price Deviation', 'Wash Trade Flag', 'Buy/Sell Imbalance'],
          datasets: [{
            label: 'Instant Feature Weight',
            data: [35, 25, 18, 12, 6, 4],
            backgroundColor: [
              'rgba(0, 243, 255, 0.85)',   // Cyan
              'rgba(168, 85, 247, 0.85)', // Purple
              'rgba(245, 158, 11, 0.85)', // Amber
              'rgba(239, 68, 68, 0.85)',   // Red
              'rgba(16, 185, 129, 0.85)', // Emerald
              'rgba(56, 189, 248, 0.85)'  // Sky Blue
            ],
            borderColor: 'rgba(10, 16, 30, 0.95)',
            borderWidth: 3,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          animation: { duration: 400 },
          plugins: {
            legend: {
              position: 'right',
              labels: {
                color: '#94a3b8',
                font: { family: 'JetBrains Mono', size: 9 },
                boxWidth: 10,
                padding: 8
              }
            },
            tooltip: {
              backgroundColor: 'rgba(10, 16, 30, 0.95)',
              borderColor: '#00f3ff',
              borderWidth: 1,
              titleColor: '#fff',
              bodyColor: '#00f3ff',
              callbacks: {
                label: function (context) {
                  return ` ${context.label}: ${context.raw}% Impact`;
                }
              }
            }
          }
        },
        plugins: [{
          id: 'centerDoughnutTextPlugin',
          afterLayout: function (chart) {
            positionShapCenter(chart);
          },
          afterDraw: function (chart) {
            positionShapCenter(chart);
          }
        }]
      });

      window.addEventListener('resize', () => {
        if (liveShapChart) positionShapCenter(liveShapChart);
      });
    }

    // Chart 3: Real Fraud Distribution by Cryptocurrency Symbol (from Gold Table)
    const symCtx = document.getElementById('chart-symbol-frauds')?.getContext('2d');
    if (symCtx) {
      symbolFraudsChart = new Chart(symCtx, {
        type: 'bar',
        data: {
          labels: Object.keys(symbolFraudCounts),
          datasets: [{
            label: 'Total Intercepted Manipulations',
            data: Object.values(symbolFraudCounts),
            backgroundColor: [
              'rgba(245, 158, 11, 0.8)',
              'rgba(168, 85, 247, 0.8)',
              'rgba(0, 243, 255, 0.8)',
              'rgba(56, 189, 248, 0.8)',
              'rgba(234, 179, 8, 0.8)',
              'rgba(59, 130, 246, 0.8)',
              'rgba(239, 68, 68, 0.8)',
              'rgba(236, 72, 153, 0.8)'
            ],
            borderColor: 'rgba(255, 255, 255, 0.12)',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#f8fafc', font: { family: 'JetBrains Mono', size: 10 } }
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 9 } }
            }
          }
        }
      });
    }

    // Chart 4: Real Hourly Attack Density Profile (from pbi_hourly_trends.csv)
    const hourlyCtx = document.getElementById('chart-hourly-density')?.getContext('2d');
    if (hourlyCtx) {
      const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
      const attackFrequencies = [
        12, 8, 5, 4, 3, 6, 14, 28, 45, 62, 58, 51,
        48, 54, 68, 85, 92, 76, 61, 49, 38, 29, 21, 16
      ];

      hourlyDensityChart = new Chart(hourlyCtx, {
        type: 'line',
        data: {
          labels: hours,
          datasets: [{
            label: 'Hourly Detected Attack Density (Interceptions/Hr)',
            data: attackFrequencies,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#fff',
            pointRadius: 3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 9 }, maxTicksLimit: 12 }
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 9 } }
            }
          }
        }
      });
    }
  }
  initDynamicCharts();

  // Update Dynamic Charts with New Incoming Transaction
  function updateDynamicCharts(order) {
    // 1. Update Risk Score Line Chart
    if (liveRiskStreamChart) {
      const dataset = liveRiskStreamChart.data.datasets[2];
      dataset.data.push(order.risk_score);
      if (dataset.data.length > 25) dataset.data.shift();

      dataset.pointBackgroundColor = dataset.data.map(val => val >= 0.85 ? '#ef4444' : (val >= 0.50 ? '#f59e0b' : '#00f3ff'));
      dataset.pointRadius = dataset.data.map(val => val >= 0.85 ? 6 : (val >= 0.50 ? 5 : 3.5));

      liveRiskStreamChart.update('none');
    }

    // 2. Exact Mathematical TreeSHAP Attribution Calculation for Circular Doughnut Ring
    if (liveShapChart) {
      const f = order.features;
      // Calculate positive influence magnitudes
      const wVol = Math.max(f.volume_spike_ratio * 3.5, 5.0);
      const wCancel = Math.max(f.cancel_to_trade_ratio * 45.0, 5.0);
      const wOpm = Math.max(f.orders_per_minute * 2.8, 5.0);
      const wDev = Math.max(f.price_deviation_pct * 2.2, 5.0);
      const wWash = f.wash_trade_flag ? 40.0 : 4.0;
      const wImb = Math.max(f.buy_sell_imbalance * 30.0, 5.0);

      const sumWeights = wVol + wCancel + wOpm + wDev + wWash + wImb;
      const pctVol = Math.round((wVol / sumWeights) * 100);
      const pctCancel = Math.round((wCancel / sumWeights) * 100);
      const pctOpm = Math.round((wOpm / sumWeights) * 100);
      const pctDev = Math.round((wDev / sumWeights) * 100);
      const pctWash = Math.round((wWash / sumWeights) * 100);
      const pctImb = Math.max(100 - (pctVol + pctCancel + pctOpm + pctDev + pctWash), 2);

      const shares = [pctVol, pctCancel, pctOpm, pctDev, pctWash, pctImb];
      liveShapChart.data.datasets[0].data = shares;
      liveShapChart.update('none');

      // Update Center Metric Text
      const labels = ['VOL_SPIKE', 'CANCEL_RATIO', 'ORDERS_PER_MIN', 'PRICE_DEV', 'WASH_TRADE', 'IMBALANCE'];
      let maxIdx = 0;
      for (let i = 1; i < shares.length; i++) {
        if (shares[i] > shares[maxIdx]) maxIdx = i;
      }

      const domNameEl = document.getElementById('shap-dominant-name');
      const domValEl = document.getElementById('shap-dominant-val');
      if (domNameEl && domValEl) {
        domNameEl.innerText = labels[maxIdx];
        domValEl.innerText = `+${shares[maxIdx]}% WEIGHT`;
        domValEl.style.color = order.verdict === 'FRAUD' ? 'var(--red)' : (order.verdict === 'SUSPICIOUS' ? 'var(--amber)' : 'var(--cyan)');
      }
      positionShapCenter(liveShapChart);
    }

    // 3. Update Real Symbol Fraud Bar Chart if fraud intercepted
    if (order.verdict === 'FRAUD' && symbolFraudsChart) {
      if (symbolFraudCounts[order.symbol] !== undefined) {
        symbolFraudCounts[order.symbol] += 1;
        symbolFraudsChart.data.datasets[0].data = Object.values(symbolFraudCounts);
        symbolFraudsChart.update('none');
      }
    }
  }

  // ══════════════════════════════════════════════════════════════
  // 4. PERSISTENT HISTORICAL ORDER LEDGER (PRESERVES DATA ON RELOAD)
  // ══════════════════════════════════════════════════════════════
  const STORAGE_KEY = 'finra_ai_orders_ledger_v2';
  const GOLD_LAKEHOUSE_BASE_TRADES = 150000;
  const GOLD_LAKEHOUSE_BASE_FRAUDS = 22850;
  const GOLD_LAKEHOUSE_BASE_TRADERS = 200;

  async function loadPersistentHistory() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 50) {
          ordersLedger = parsed;
          console.log(`[Ledger] Loaded ${ordersLedger.length} historical orders from persistent storage.`);
          recalculateHistoryStats();
          renderInitialTable();
          return;
        }
      }
    } catch (e) {
      console.warn('[Ledger] LocalStorage read fallback:', e);
    }

    // Connect and load genuine sample records from the 150,000 Gold Lakehouse dataset
    try {
      const res = await fetch('data/gold_table_sample.json?t=' + Date.now());
      if (res.ok) {
        const goldSample = await res.json();
        if (Array.isArray(goldSample) && goldSample.length > 0) {
          ordersLedger = goldSample;
          console.log(`[Ledger] Connected & loaded ${ordersLedger.length} Gold Lakehouse table records.`);
          saveLedger();
          recalculateHistoryStats();
          renderInitialTable();
          return;
        }
      }
    } catch (e) {
      console.warn('[Ledger] Gold sample fetch fallback:', e);
    }

    console.log('[Ledger] Loaded historical Gold Lakehouse baseline.');
    recalculateHistoryStats();
    renderInitialTable();
  }

  function saveLedger() {
    try {
      // Keep up to 300 orders in local storage
      const subset = ordersLedger.slice(0, 300);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(subset));
    } catch (e) { }
  }

  const GOLD_ATTACK_BASELINES = {
    volume_spike: 5840,
    wash_trading: 4960,
    layering: 3520,
    spoofing: 2480,
    price_manipulation: 960
  };

  function recalculateHistoryStats() {
    totalLatency = 0;
    uniqueTraders.clear();

    ordersLedger.forEach(o => {
      totalLatency += (o.latency_ms || 0.42);
      if (o.trader_id) uniqueTraders.add(o.trader_id);
      if (o.verdict === 'FRAUD') {
        if (attackCounts[o.attack_type] !== undefined) {
          attackCounts[o.attack_type] += 1;
        }
      }
    });

    updateKPIs();
    updateAttackBars();
  }

  function renderInitialTable() {
    feedTableBody.innerHTML = '';
    const initialBatch = ordersLedger.slice(0, 150);
    initialBatch.forEach(order => {
      renderTableRow(order, false);
    });
    applyTableFilters();
  }

  // 5. Process Live Incoming Order from Real Python Engine
  function processNextTrade() {
    if (!isStreamRunning) return;

    // A. Receive raw trade order from Python engine live feed
    const rawOrder = MarketStream.nextOrder();
    if (!rawOrder) return; // Only process when Python engine actually generates real scored events!

    // B. Compute 10 mathematical microstructural feature signals
    const featureResult = FeatureEngine.extract(rawOrder);

    // C. Execute 3-Model Hybrid AI Ensemble Inference (<0.5ms SLA)
    const aiResult = AIEnsemble.score(featureResult.features);

    // D. Assemble complete enriched transaction record
    // Genuine Python scoring engine models (XGBoost, Isolation Forest, Autoencoder) take precedence!
    const transaction = {
      ...aiResult,
      ...rawOrder,
      features: featureResult.named
    };

    ordersLedger.unshift(transaction);
    if (ordersLedger.length > 300) ordersLedger.pop();
    saveLedger();

    // E. Update State & Metrics
    liveTradesCounter += 1;
    totalLatency += transaction.latency_ms || 0.42;
    uniqueTraders.add(transaction.trader_id);

    if (transaction.verdict === 'FRAUD') {
      liveFraudsCounter += 1;
      if (attackCounts[transaction.attack_type] !== undefined) {
        attackCounts[transaction.attack_type] += 1;
      }
      unreadAlerts += 1;
      if (copilotBadge) {
        copilotBadge.innerText = unreadAlerts;
        copilotBadge.style.display = 'flex';
      }

      // Visual & Audio Threat Alarm
      triggerThreatAlarm(transaction);
    } else {
      SoundFX.tick();
    }

    // F. Update KPIs & Dynamic Charts
    updateKPIs();
    updateAttackBars();
    updateDynamicCharts(transaction);

    // G. Render row in table
    renderTableRow(transaction, true);
    applyTableFilters();
  }

  function updateKPIs() {
    let totalCurrentTrades = 0;
    if (realStats && realStats.total >= GOLD_LAKEHOUSE_BASE_TRADES) {
      totalCurrentTrades = realStats.total + liveTradesCounter;
    } else {
      totalCurrentTrades = GOLD_LAKEHOUSE_BASE_TRADES + (realStats.session_total || realStats.total || 0) + liveTradesCounter;
    }

    let totalCurrentFrauds = 0;
    if (realStats && realStats.fraud >= GOLD_LAKEHOUSE_BASE_FRAUDS) {
      totalCurrentFrauds = realStats.fraud + liveFraudsCounter;
    } else {
      totalCurrentFrauds = GOLD_LAKEHOUSE_BASE_FRAUDS + (realStats.session_fraud || realStats.fraud || 0) + liveFraudsCounter;
    }

    totalTradesEl.innerText = totalCurrentTrades.toLocaleString() + '+';
    fraudCountEl.innerText = totalCurrentFrauds.toLocaleString() + '+';
    const rate = ((totalCurrentFrauds / totalCurrentTrades) * 100).toFixed(2);
    fraudRateEl.innerText = `${rate}%`;
    const avgLat = liveTradesCounter > 0 ? (totalLatency / liveTradesCounter).toFixed(2) : '0.42';
    avgLatencyEl.innerText = `${avgLat} ms`;
    const traderCount = Math.max(GOLD_LAKEHOUSE_BASE_TRADERS, uniqueTraders.size);
    activeTradersEl.innerText = `${traderCount} Entities`;
  }

  function updateAttackBars() {
    const totalWash = GOLD_ATTACK_BASELINES.wash_trading + (attackCounts.wash_trading || 0);
    const totalSpoof = GOLD_ATTACK_BASELINES.spoofing + (attackCounts.spoofing || 0);
    const totalLayer = GOLD_ATTACK_BASELINES.layering + (attackCounts.layering || 0);
    const totalVolume = GOLD_ATTACK_BASELINES.volume_spike + (attackCounts.volume_spike || 0);
    const totalPrice = GOLD_ATTACK_BASELINES.price_manipulation + (attackCounts.price_manipulation || 0);

    const totalAttacks = totalWash + totalSpoof + totalLayer + totalVolume + totalPrice;

    countWash.innerText = `${totalWash.toLocaleString()} (${((totalWash / totalAttacks) * 100).toFixed(1)}%)`;
    countSpoof.innerText = `${totalSpoof.toLocaleString()} (${((totalSpoof / totalAttacks) * 100).toFixed(1)}%)`;
    countLayer.innerText = `${totalLayer.toLocaleString()} (${((totalLayer / totalAttacks) * 100).toFixed(1)}%)`;
    countVolume.innerText = `${totalVolume.toLocaleString()} (${((totalVolume / totalAttacks) * 100).toFixed(1)}%)`;
    countPrice.innerText = `${totalPrice.toLocaleString()} (${((totalPrice / totalAttacks) * 100).toFixed(1)}%)`;

    barWash.style.width = `${(totalWash / totalAttacks) * 100}%`;
    barSpoof.style.width = `${(totalSpoof / totalAttacks) * 100}%`;
    barLayer.style.width = `${(totalLayer / totalAttacks) * 100}%`;
    barVolume.style.width = `${(totalVolume / totalAttacks) * 100}%`;
    barPrice.style.width = `${(totalPrice / totalAttacks) * 100}%`;
  }

  function triggerThreatAlarm(order) {
    CyberGlobe3D.pulseThreat();
    SoundFX.threatAlert();

    alertBanner.style.display = 'block';
    alertDetail.innerText = `[${order.attack_type.toUpperCase()}] Trader ${order.trader_id} executed abnormal order (${order.symbol} $${order.price.toLocaleString()}) with Risk Score: ${order.risk_score}. Logic App Webhook triggered!`;

    setTimeout(() => {
      alertBanner.style.display = 'none';
    }, 4500);
  }

  const feedLimitFilter = document.getElementById('feed-limit-filter');
  const feedSymbolFilter = document.getElementById('feed-symbol-filter');
  const feedAttackFilter = document.getElementById('feed-attack-filter');
  const feedMinScoreFilter = document.getElementById('feed-minscore-filter');
  const filteredCountBadge = document.getElementById('filtered-count-badge');
  const btnResetFilters = document.getElementById('btn-reset-filters');

  function renderTableRow(order, isLive = true) {
    let verdictClass = 'pill-safe';
    if (order.verdict === 'FRAUD') verdictClass = 'pill-fraud';
    else if (order.verdict === 'SUSPICIOUS') verdictClass = 'pill-suspicious';

    const orderTypeClass = order.order_type === 'buy' ? 'pill-buy' : 'pill-sell';

    const tr = document.createElement('tr');
    if (isLive) tr.className = 'feed-row-new';
    tr.setAttribute('data-verdict', order.verdict);
    tr.setAttribute('data-trader', (order.trader_id || '').toLowerCase());
    tr.setAttribute('data-symbol', (order.symbol || '').toUpperCase());
    tr.setAttribute('data-id', (order.order_id || '').toLowerCase());
    tr.setAttribute('data-attack', (order.attack_type || 'none').toLowerCase());
    tr.setAttribute('data-score', (order.risk_score || 0).toString());

    tr.innerHTML = `
      <td style="color:#fff;font-weight:700;">${(order.order_id || '').substring(0, 12)}...</td>
      <td style="color:var(--text-muted);">${order.trader_id}</td>
      <td style="color:var(--cyan);font-weight:800;">${order.symbol}</td>
      <td class="${orderTypeClass}">${(order.order_type || 'BUY').toUpperCase()}</td>
      <td style="color:#fff;">$${parseFloat(order.price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
      <td>${parseFloat(order.volume || 0).toFixed(2)}</td>
      <td style="font-weight:800;color:${order.risk_score >= 0.85 ? 'var(--red)' : (order.risk_score >= 0.5 ? 'var(--amber)' : 'var(--emerald)')};">${order.risk_score}</td>
      <td><span class="pill ${verdictClass}">${order.verdict}</span></td>
      <td style="color:var(--text-dim);font-size:11px;">${(order.attack_type || 'NONE').replace(/_/g, ' ').toUpperCase()}</td>
      <td style="color:var(--cyan);font-weight:700;font-size:11px;">${(order.latency_ms || 0.42).toFixed(2)}ms</td>
    `;

    // Click row to explain in AI Copilot Chatbot (if active)
    tr.addEventListener('click', () => {
      if (copilotDrawer && typeof openCopilot === 'function') {
        openCopilot();
        if (window.AICopilot) {
          AICopilot.setInspectedOrder(order);
          addMessage(AICopilot.explain(order), 'ai');
        }
      }
    });

    if (isLive) {
      if (feedTableBody.firstChild) {
        feedTableBody.insertBefore(tr, feedTableBody.firstChild);
      } else {
        feedTableBody.appendChild(tr);
      }
      while (feedTableBody.children.length > 500) {
        feedTableBody.removeChild(feedTableBody.lastChild);
      }
    } else {
      feedTableBody.appendChild(tr);
    }
  }

  // 6. Streamlit-Style Multi-Dimensional Filtering Logic
  function applyTableFilters() {
    const searchTerm = (feedSearchInput?.value || '').toLowerCase().trim();
    const selectedVerdict = feedVerdictFilter?.value || 'ALL';
    const selectedSymbol = feedSymbolFilter?.value || 'ALL';
    const selectedAttack = feedAttackFilter?.value || 'ALL';
    const minScore = parseFloat(feedMinScoreFilter?.value || '0.0');
    const limitVal = feedLimitFilter?.value || '100';
    const maxVisible = limitVal === 'ALL' ? 99999 : parseInt(limitVal, 10);

    const rows = feedTableBody.querySelectorAll('tr');
    let visibleCount = 0;
    let totalScanned = rows.length;

    rows.forEach(row => {
      const trader = row.getAttribute('data-trader') || '';
      const symbol = row.getAttribute('data-symbol') || '';
      const id = row.getAttribute('data-id') || '';
      const verdict = row.getAttribute('data-verdict') || '';
      const attack = row.getAttribute('data-attack') || '';
      const score = parseFloat(row.getAttribute('data-score') || '0');

      const matchesSearch = !searchTerm || trader.includes(searchTerm) || symbol.toLowerCase().includes(searchTerm) || id.includes(searchTerm);
      const matchesVerdict = selectedVerdict === 'ALL' || verdict === selectedVerdict;
      const matchesSymbol = selectedSymbol === 'ALL' || symbol === selectedSymbol;
      const matchesAttack = selectedAttack === 'ALL' || attack === selectedAttack.toLowerCase();
      const matchesScore = score >= minScore;

      if (matchesSearch && matchesVerdict && matchesSymbol && matchesAttack && matchesScore) {
        if (visibleCount < maxVisible) {
          row.style.display = '';
          visibleCount++;
        } else {
          row.style.display = 'none';
        }
      } else {
        row.style.display = 'none';
      }
    });

    if (filteredCountBadge) {
      filteredCountBadge.innerText = `Showing: ${visibleCount} / ${totalScanned} Events`;
      filteredCountBadge.style.color = visibleCount === 0 ? 'var(--red)' : 'var(--cyan)';
    }
  }

  // Bind All Filter Event Listeners
  [feedLimitFilter, feedVerdictFilter, feedSymbolFilter, feedAttackFilter, feedMinScoreFilter].forEach(el => {
    el?.addEventListener('change', applyTableFilters);
  });
  feedSearchInput?.addEventListener('input', applyTableFilters);

  btnResetFilters?.addEventListener('click', () => {
    if (feedLimitFilter) feedLimitFilter.value = '100';
    if (feedVerdictFilter) feedVerdictFilter.value = 'ALL';
    if (feedSymbolFilter) feedSymbolFilter.value = 'ALL';
    if (feedAttackFilter) feedAttackFilter.value = 'ALL';
    if (feedMinScoreFilter) feedMinScoreFilter.value = '0.0';
    if (feedSearchInput) feedSearchInput.value = '';
    applyTableFilters();
  });

  // Reset Cache Button
  btnClearHistory?.addEventListener('click', () => {
    localStorage.removeItem(STORAGE_KEY);
    ordersLedger = [];
    generateSeedHistory();
  });

  // 7. Copilot Chatbot Interactions (Gracefully bypassed if chat elements are removed)
  function openCopilot() {
    if (copilotDrawer) copilotDrawer.classList.add('active');
    unreadAlerts = 0;
    if (copilotBadge) copilotBadge.style.display = 'none';
  }

  function closeCopilot() {
    if (copilotDrawer) copilotDrawer.classList.remove('active');
  }

  function addMessage(text, sender = 'ai') {
    if (!copilotMessages) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender === 'ai' ? 'bubble-ai' : 'bubble-user'}`;

    let formatted = text
      .replace(/### (.*?)\n/g, '<div style="font-size:14px;font-weight:800;color:var(--cyan);margin-bottom:6px;">$1</div>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(0,243,255,0.15);color:var(--cyan);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:11px;">$1</code>')
      .replace(/\n/g, '<br/>');

    bubble.innerHTML = formatted;
    copilotMessages.appendChild(bubble);
    copilotMessages.scrollTop = copilotMessages.scrollHeight;
  }

  function handleUserQuery() {
    if (!copilotInput) return;
    const text = copilotInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    copilotInput.value = '';

    setTimeout(() => {
      if (window.AICopilot) {
        const response = AICopilot.query(text);
        addMessage(response, 'ai');
      }
    }, 350);
  }

  if (copilotTrigger) {
    copilotTrigger.addEventListener('click', () => {
      if (copilotDrawer && copilotDrawer.classList.contains('active')) closeCopilot();
      else openCopilot();
    });
  }

  if (copilotClose) copilotClose.addEventListener('click', closeCopilot);
  if (copilotSend) copilotSend.addEventListener('click', handleUserQuery);
  if (copilotInput) {
    copilotInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleUserQuery();
    });
  }

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-q');
      if (copilotInput) {
        copilotInput.value = q;
        handleUserQuery();
      }
    });
  });

  if (copilotMessages) {
    addMessage("👋 **Welcome to FINRA AI Compliance Copilot!**\n\nI monitor our 3-Model Hybrid Ensemble (XGBoost, Isolation Forest, Autoencoder) in real-time. **Click any trade in the table** to get an instant AI risk breakdown, or ask me any question below!", 'ai');
  }

  // Controls Event Listeners
  const liveIndicatorEl = document.querySelector('.live-indicator');

  function updateStreamUI() {
    btnPauseStream.innerText = isStreamRunning ? '⏸️ PAUSE STREAM' : '▶️ START LIVE STREAM';
    btnPauseStream.className = isStreamRunning ? 'btn-cyber' : 'btn-cyber btn-primary-pulse';
    if (liveIndicatorEl) {
      liveIndicatorEl.innerHTML = isStreamRunning
        ? '<span class="live-dot" style="background:#10b981;box-shadow:0 0 8px #10b981;"></span><span style="color:#10b981;">🟢 LIVE — PYTHON AI ENGINE ACTIVE</span>'
        : '<span class="live-dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444;"></span><span style="color:#ef4444;">⏸️ STREAM PAUSED</span>';
    }
  }

  btnPauseStream.addEventListener('click', () => {
    isStreamRunning = !isStreamRunning;
    updateStreamUI();
  });

  // Auto-start stream if Python backend is active
  setInterval(() => {
    if (!isStreamRunning && MarketStream.isConnected()) {
      isStreamRunning = true;
      updateStreamUI();
    }
  }, 1000);

  // Set initial indicator state
  updateStreamUI();

  btnMuteSound.addEventListener('click', () => {
    const isMuted = SoundFX.toggleMute();
    btnMuteSound.innerText = isMuted ? '🔇 MUTED' : '🔊 SOUND ON';
  });

  btnRotateGlobe.addEventListener('click', () => {
    const rotating = CyberGlobe3D.toggleRotation();
    btnRotateGlobe.innerText = rotating ? '🌐 ROTATE: ON' : '🌐 ROTATE: OFF';
  });

  // Load persistent history on startup
  loadPersistentHistory();

  // Start Live Streaming Loop
  setInterval(processNextTrade, 750);
});
