/**
 * feature_engine.js
 * Implements rolling symbol and trader memory buffers to calculate the exact
 * 10 mathematical microstructural feature signals for AI model ingestion.
 */

const FeatureEngine = (() => {
  // Memory buffers
  const symbolWindows = {};
  const traderWindows = {};
  const EPSILON = 1e-9;
  const WINDOW_SIZE = 25;

  function initBuffers(symbol) {
    if (!symbolWindows[symbol]) {
      symbolWindows[symbol] = {
        volumes: [],
        prices: []
      };
    }
  }

  function initTrader(traderId) {
    if (!traderWindows[traderId]) {
      traderWindows[traderId] = {
        timestamps: [],
        cancels: 0,
        total: 0,
        buys: 0,
        sells: 0
      };
    }
  }

  function computeFeatures(order) {
    const sym = order.symbol;
    const tid = order.trader_id;
    const now = Date.now();

    initBuffers(sym);
    initTrader(tid);

    const sWin = symbolWindows[sym];
    const tWin = traderWindows[tid];

    // 1. Update Symbol Buffer
    sWin.volumes.push(order.volume);
    sWin.prices.push(order.price);
    if (sWin.volumes.length > WINDOW_SIZE) sWin.volumes.shift();
    if (sWin.prices.length > WINDOW_SIZE) sWin.prices.shift();

    const avgVol = sWin.volumes.reduce((a, b) => a + b, 0) / sWin.volumes.length;
    const avgPrice = sWin.prices.reduce((a, b) => a + b, 0) / sWin.prices.length;

    // 2. Update Trader Buffer
    tWin.total += 1;
    if (order.order_status === 'cancelled') tWin.cancels += 1;
    if (order.order_type === 'buy') tWin.buys += 1;
    if (order.order_type === 'sell') tWin.sells += 1;
    tWin.timestamps.push(now);

    // Keep only timestamps within past 60s
    tWin.timestamps = tWin.timestamps.filter(t => now - t <= 60000);
    const ordersPerMinute = tWin.timestamps.length;

    // 3. Compute Exact 10 Mathematical Feature Signals
    
    // F1: Volume Spike Ratio
    const volumeSpikeRatio = order.volume / (avgVol + EPSILON);

    // F2: Price Range / Volatility %
    const priceRangePct = Math.abs(order.price_change_24h_pct || 0);

    // F3: Cancel-to-Trade Ratio
    const cancelToTradeRatio = tWin.cancels / (tWin.total + EPSILON);

    // F4: Wash Trading Indicator (Self-dealing / circular order flow)
    const washTradeFlag = (cancelToTradeRatio > 0.45 && volumeSpikeRatio > 3.5) || (tWin.buys > 2 && tWin.sells > 2 && volumeSpikeRatio > 2.0) ? 1.0 : 0.0;

    // F5: Layering Indicator (High velocity + cancellation across depth)
    const layeringFlag = (ordersPerMinute >= 10 && cancelToTradeRatio > 0.40) || (ordersPerMinute >= 15) ? 1.0 : 0.0;

    // F6: Orders Per Minute
    const opm = ordersPerMinute;

    // F7: Buy-Sell Imbalance Ratio [0.0 - 1.0]
    const buySellImbalance = Math.abs(tWin.buys - tWin.sells) / (tWin.buys + tWin.sells + EPSILON);

    // F8: Price Deviation % from prevailing market fair value
    const priceDeviationPct = (Math.abs(order.price - avgPrice) / (avgPrice + EPSILON)) * 100;

    // F9: Raw Volume
    const volume = order.volume;

    // F10: Raw Price
    const price = order.price;

    return {
      features: [
        volumeSpikeRatio,
        priceRangePct,
        cancelToTradeRatio,
        washTradeFlag,
        layeringFlag,
        opm,
        buySellImbalance,
        priceDeviationPct,
        volume,
        price
      ],
      named: {
        volume_spike_ratio: volumeSpikeRatio,
        price_range_pct: priceRangePct,
        cancel_to_trade_ratio: cancelToTradeRatio,
        wash_trade_flag: washTradeFlag,
        layering_flag: layeringFlag,
        orders_per_minute: opm,
        buy_sell_imbalance: buySellImbalance,
        price_deviation_pct: priceDeviationPct,
        volume: volume,
        price: price
      }
    };
  }

  return {
    extract: computeFeatures
  };
})();
