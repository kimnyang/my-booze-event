let chart;
let angle = 0;
let spinning = false;

async function fetchData() {
    try {
        const response = await fetch('/data');
        const data = await response.json();

        const { timestamps, prices, market_open } = data;
        updateChart(timestamps, prices);

        const status = document.getElementById("market-status");
        status.style.display = market_open ? "none" : "inline-block";
    } catch (error) {
        console.error("데이터 불러오기 실패:", error);
    }
}

function createChart(labels, values) {
    const ctx = document.getElementById("priceChart").getContext("2d");
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '가격 (₩)',
                data: values,
                borderColor: '#4a90e2',
                backgroundColor: 'rgba(74,144,226,0.15)',
                borderWidth: 3,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            scales: {
                y: {
                    min: 2500,
                    max: 5000,
                    ticks: { stepSize: 500 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function updateChart(labels, values) {
    if (!chart) {
        createChart(labels, values);
    } else {
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.update();
    }
}

// 돌림판 기능
document.getElementById("spinBtn").addEventListener("click", () => {
    if (spinning) return;
    spinning = true;
    const wheel = document.getElementById("wheel");
    const randomDeg = 360 * 5 + Math.floor(Math.random() * 360);
    wheel.style.transform = `rotate(${angle + randomDeg}deg)`;
    angle += randomDeg;

    setTimeout(() => {
        spinning = false;
        alert("🎉 축하합니다! 이벤트 결과가 나왔습니다!");
    }, 4200);
});

// 초기 로드
fetchData();
setInterval(fetchData, 150000);  // 2분 30초마다 업데이트