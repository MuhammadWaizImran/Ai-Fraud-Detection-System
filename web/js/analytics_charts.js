/**
 * analytics_charts.js
 * Renders Streamlit-grade SHAP Global Feature Importance and Hourly Attack Density profiles using Chart.js.
 */

const AnalyticsCharts = (() => {
  let shapChart = null;
  let densityChart = null;

  function init() {
    initShapChart();
    initHourlyDensityChart();
  }

  function initShapChart() {
    const ctx = document.getElementById('chart-shap-importance')?.getContext('2d');
    if (!ctx) return;

    shapChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [
          'volume_spike_ratio',
          'cancel_to_trade_ratio',
          'orders_per_minute',
          'price_deviation_pct',
          'wash_trade_flag',
          'buy_sell_imbalance',
          'layering_flag',
          'price_range_pct',
          'volume',
          'price'
        ],
        datasets: [{
          label: 'Mean |SHAP Value| (Impact on Model Risk Score)',
          data: [0.421, 0.342, 0.264, 0.218, 0.185, 0.142, 0.119, 0.084, 0.052, 0.031],
          backgroundColor: [
            'rgba(0, 243, 255, 0.85)',
            'rgba(0, 243, 255, 0.75)',
            'rgba(168, 85, 247, 0.85)',
            'rgba(168, 85, 247, 0.75)',
            'rgba(245, 158, 11, 0.85)',
            'rgba(245, 158, 11, 0.75)',
            'rgba(239, 68, 68, 0.85)',
            'rgba(239, 68, 68, 0.75)',
            'rgba(16, 185, 129, 0.85)',
            'rgba(16, 185, 129, 0.75)'
          ],
          borderColor: 'rgba(255, 255, 255, 0.15)',
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y', // Horizontal bars
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
              label: (ctx) => ` Feature Importance Weight: ${ctx.parsed.x.toFixed(3)}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y: {
            grid: { display: false },
            ticks: { color: '#f8fafc', font: { family: 'JetBrains Mono', size: 11 } }
          }
        }
      }
    });
  }

  function initHourlyDensityChart() {
    const ctx = document.getElementById('chart-hourly-density')?.getContext('2d');
    if (!ctx) return;

    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    const attackFrequencies = [
      12, 8, 5, 4, 3, 6, 14, 28, 45, 62, 58, 51,
      48, 54, 68, 85, 92, 76, 61, 49, 38, 29, 21, 16
    ];

    densityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: hours,
        datasets: [{
          label: 'Hourly Detected Attack Density (Interceptions/Hr)',
          data: attackFrequencies,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ef4444',
          pointBorderColor: '#fff',
          pointRadius: 3,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(10, 16, 30, 0.95)',
            borderColor: '#ef4444',
            borderWidth: 1,
            titleColor: '#fff',
            bodyColor: '#ff6b6b',
            callbacks: {
              label: (ctx) => ` Peak Density: ${ctx.parsed.y} attacks/hr`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 9 }, maxTicksLimit: 12 }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
          }
        }
      }
    });
  }

  return {
    init: init
  };
})();
