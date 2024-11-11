document.addEventListener('DOMContentLoaded', () => {
    // Пример обновления данных
    document.getElementById('overallPerformance').textContent = '75%';
    document.getElementById('failedMetrics').textContent = 'FCP, TBT';
    document.getElementById('loadLevel').textContent = 'Высокий';
    document.getElementById('fcpTrend').textContent = 'Улучшение';
    document.getElementById('fcpTrend').classList.add('trend-up');
    document.getElementById('lcpTrend').textContent = 'Стабильный';
    document.getElementById('lcpTrend').classList.add('trend-neutral');
    document.getElementById('ttfbTrend').textContent = 'Ухудшение';
    document.getElementById('ttfbTrend').classList.add('trend-down');
    document.getElementById('tbtTrend').textContent = 'Стабильный';
    document.getElementById('tbtTrend').classList.add('trend-neutral');
});
