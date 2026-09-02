/**
 * market_stream.js
 * Fetches live real-world crypto prices from CoinGecko API
 * and generates authentic trading order stream with manipulation scenarios.
 */

const MarketStream = (() => {
  const SYMBOLS = [
    { id: 'bitcoin', symbol: 'BTC', name: 'Bitcoin', basePrice: 65420.00, volFactor: 0.05 },
    { id: 'ethereum', symbol: 'ETH', name: 'Ethereum', basePrice: 3450.50, volFactor: 0.5 },
    { id: 'solana', symbol: 'SOL', name: 'Solana', basePrice: 142.80, volFactor: 5.0 },
    { id: 'binancecoin', symbol: 'BNB', name: 'Binance Coin', basePrice: 585.20, volFactor: 1.5 },
    { id: 'ripple', symbol: 'XRP', name: 'Ripple', basePrice: 0.582, volFactor: 500.0 },
    { id: 'dogecoin', symbol: 'DOGE', name: 'Dogecoin', basePrice: 0.124, volFactor: 2000.0 },
    { id: 'cardano', symbol: 'ADA', name: 'Cardano', basePrice: 0.385, volFactor: 800.0 },
    { id: 'polkadot', symbol: 'DOT', name: 'Polkadot', basePrice: 4.85, volFactor: 80.0 }
  ];

  let currentPrices = {};
  SYMBOLS.forEach(s => {
    currentPrices[s.symbol] = {
      price: s.basePrice,
      change24h: (Math.random() * 6 - 3).toFixed(2),
      name: s.name,
      id: s.id
    };
  });

  // Fetch real CoinGecko prices
  async function updateRealPrices() {
    try {
      const ids = SYMBOLS.map(s => s.id).join(',');
      const res = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true`);
      if (res.ok) {
        const data = await res.json();
        SYMBOLS.forEach(s => {
          if (data[s.id] && data[s.id].usd) {
            currentPrices[s.symbol].price = data[s.id].usd;
            currentPrices[s.symbol].change24h = data[s.id].usd_24h_change ? data[s.id].usd_24h_change.toFixed(2) : currentPrices[s.symbol].change24h;
          }
        });
        console.log('[MarketStream] Live CoinGecko prices updated successfully');
      }
    } catch (e) {
      console.warn('[MarketStream] Live fetch fallback to local drift:', e.message);
    }
  }

  // Update prices periodically
  updateRealPrices();
  setInterval(updateRealPrices, 45000);

  // Generate authentic trading orders
  const TRADERS = Array.from({ length: 80 }, (_, i) => `TRADER_${String(i + 1).padStart(4, '0')}`);
  const SUSPICIOUS_TRADERS = ['TRADER_0012', 'TRADER_0042', 'TRADER_0068', 'TRADER_0077', 'TRADER_0099', 'TRADER_0103'];

  function generateTradeOrder() {
    const symObj = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
    const symbol = symObj.symbol;
    const baseInfo = currentPrices[symbol];
    
    // 15% probability of injected attack pattern
    const isAttack = Math.random() < 0.16;
    let traderId = isAttack 
      ? SUSPICIOUS_TRADERS[Math.floor(Math.random() * SUSPICIOUS_TRADERS.length)]
      : TRADERS[Math.floor(Math.random() * TRADERS.length)];

    let orderType = Math.random() > 0.48 ? 'buy' : 'sell';
    let orderStatus = 'executed';
    let price = baseInfo.price * (1 + (Math.random() * 0.008 - 0.004));
    let volume = (Math.random() * 5 + 0.5) * symObj.volFactor;
    let attackType = 'none';

    if (isAttack) {
      const scenarios = ['wash_trading', 'spoofing', 'layering', 'volume_spike', 'price_manipulation'];
      attackType = scenarios[Math.floor(Math.random() * scenarios.length)];

      if (attackType === 'volume_spike') {
        volume = volume * (Math.random() * 25 + 15); // 15x - 40x spike
      } else if (attackType === 'spoofing') {
        orderStatus = 'cancelled';
        volume = volume * (Math.random() * 12 + 8);
      } else if (attackType === 'layering') {
        orderStatus = Math.random() > 0.3 ? 'cancelled' : 'executed';
        volume = volume * (Math.random() * 8 + 4);
      } else if (attackType === 'price_manipulation') {
        price = price * (Math.random() > 0.5 ? 1.18 : 0.82); // 18% off-market
      } else if (attackType === 'wash_trading') {
        volume = volume * (Math.random() * 10 + 5);
      }
    }

    const uuid = 'ord-' + Math.random().toString(36).substring(2, 10) + '-' + Date.now().toString(36);

    return {
      order_id: uuid,
      trader_id: traderId,
      symbol: symbol,
      coin_name: symObj.name,
      order_type: orderType,
      order_status: orderStatus,
      price: parseFloat(price.toFixed(price > 100 ? 2 : 4)),
      volume: parseFloat(volume.toFixed(2)),
      price_change_24h_pct: parseFloat(baseInfo.change24h),
      timestamp: new Date().toISOString(),
      simulated_intent: attackType
    };
  }

  return {
    getPrices: () => currentPrices,
    getSymbols: () => SYMBOLS,
    nextOrder: generateTradeOrder
  };
})();
