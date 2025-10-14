document.addEventListener("DOMContentLoaded", function() {
    // ===== 차트 변수 =====
    const visiblePoints = 20, scrollStep = 10;
    let scrollStart = 0, firstLoad = true;
    let timestamps = ["시작"], prices = [5000];

    // Chart.js 초기화
    const ctxChart = document.getElementById('chart').getContext('2d');
    const chart = new Chart(ctxChart, {
        type:'line',
        data: { labels: timestamps, datasets:[{
            label:'가상코인', data: prices,
            borderColor:'rgb(75,192,192)', backgroundColor:'rgba(75,192,192,0.15)',
            pointRadius:5, pointBackgroundColor:'white', pointBorderColor:'rgb(75,192,192)', tension:0.2
        }]},
        options:{
            responsive:true, maintainAspectRatio:false,
            scales:{ x:{ticks:{maxRotation:45,minRotation:45}}, y:{min:2500,max:5000,ticks:{stepSize:500,callback:v=>v+'원'}}},
            plugins:{legend:{display:false}}
        }
    });

    // DOM요소
    const btnPrev = document.getElementById('btnPrev');
    const btnNext = document.getElementById('btnNext');
    const btnLatest = document.getElementById('btnLatest');
    const btnLowest = document.getElementById('btnLowest');
    const marketStatus = document.getElementById('marketStatus');
    const currentPriceEl = document.getElementById('currentPrice');

    btnPrev.addEventListener('click', ()=>{ scrollStart = Math.max(0, scrollStart - scrollStep); renderWindow(); });
    btnNext.addEventListener('click', ()=>{ scrollStart = Math.min(Math.max(0, timestamps.length - visiblePoints), scrollStart + scrollStep); renderWindow(); });
    btnLatest.addEventListener('click', ()=>{ scrollStart = Math.max(0, timestamps.length - visiblePoints); renderWindow(); });
    btnLowest.addEventListener('click', ()=>{ if(prices.length>0) alert("오늘의 최저가는 📉 "+Math.min(...prices)+"원 입니다!"); });

    function updateNavButtons(){
        btnPrev.disabled = (scrollStart<=0);
        btnNext.disabled = (scrollStart + visiblePoints >= timestamps.length);
    }
    function renderWindow(){
        scrollStart = Math.max(0, Math.min(scrollStart, Math.max(0, timestamps.length - visiblePoints)));
        chart.data.labels = timestamps.slice(scrollStart, scrollStart + visiblePoints);
        chart.data.datasets[0].data = prices.slice(scrollStart, scrollStart + visiblePoints);
        chart.update();
        updateNavButtons();
    }

    // ===== 서버에서 실시간 데이터 가져오기 (/data) =====
    async function fetchData(){
        try{
            const res = await fetch('/data', {cache: "no-store"});
            if(!res.ok) {
                console.warn("서버 응답 오류:", res.status);
                return;
            }
            const json = await res.json();

            if(firstLoad){
                firstLoad=false;
                timestamps = ["시작"].concat(json.timestamps || []);
                prices = [5000].concat(json.prices || []);
            } else {
                timestamps = Array.isArray(json.timestamps) ? json.timestamps.slice() : timestamps;
                prices = Array.isArray(json.prices) ? json.prices.slice() : prices;
            }

            marketStatus.style.display = json.market_open ? "none" : "inline-block";
            const latestPrice = prices.length > 0 ? prices[prices.length-1] : 5000;
            currentPriceEl.textContent = "현재가격: " + latestPrice + "원";

            renderWindow();
        } catch(e){
            console.error("fetchData 실패:", e);
        }
    }

    // 초기 fetch + 주기 (150초)
    fetchData();
    setInterval(fetchData, 150000);

    // ===== 원판 돌리기 (캔버스 기반) =====
    const wheelCanvas = document.getElementById("wheelCanvas");
    const ctx = wheelCanvas.getContext("2d");
    let optionCount = 6, options = Array(optionCount).fill(""), startAngle = 0, spinning=false;
    const colors = ["#FF9999","#FFCC66","#99CCFF","#99FF99","#FF9966","#CC99FF","#66CCCC","#FF6666"];

    // 옵션 입력 UI: renderInputs() 만들기
    function changeOptionCount(delta){
        optionCount = Math.min(8, Math.max(2, optionCount + delta));
        document.getElementById("optionCount").textContent = optionCount;
        options = Array(optionCount).fill("");
        renderInputs();
        drawWheel();
    }
    document.getElementById("optInc").addEventListener("click", ()=> changeOptionCount(1));
    document.getElementById("optDec").addEventListener("click", ()=> changeOptionCount(-1));

    function renderInputs(){
        const container = document.getElementById("optionInputs");
        container.innerHTML = "";
        options.forEach((val, i) => {
            const input = document.createElement("input");
            input.placeholder = `옵션 ${i+1}`;
            input.value = val;
            input.className = "option-input form-control";
            input.oninput = e => { options[i] = e.target.value; drawWheel(); };
            container.appendChild(input);
        });
    }

    function resizeWheelCanvasIfNeeded(){
        const rect = wheelCanvas.getBoundingClientRect();
        if (rect.width === 0) {
            // 보이지 않는 상황(탭이 비활성 등) 대비: 기본값 유지
            return;
        }
        if (wheelCanvas.width !== Math.floor(rect.width)){
            wheelCanvas.width = Math.floor(rect.width);
            wheelCanvas.height = Math.floor(rect.width);
        }
    }

    function drawWheel(){
        if(!wheelCanvas) return;
        resizeWheelCanvasIfNeeded();
        const rect = wheelCanvas.getBoundingClientRect();
        const radius = Math.min(rect.width, rect.height)/2 * 0.9;
        const centerX = rect.width/2;
        const centerY = rect.height/2;

        ctx.clearRect(0,0,wheelCanvas.width,wheelCanvas.height);
        const arc = 2*Math.PI/optionCount;
        for(let i=0;i<optionCount;i++){
            const angle = startAngle + i*arc;
            ctx.beginPath();
            ctx.moveTo(centerX,centerY);
            ctx.arc(centerX,centerY,radius,angle,angle+arc);
            ctx.closePath();
            ctx.fillStyle = colors[i%colors.length];
            ctx.fill();
            ctx.stroke();

            ctx.save();
            ctx.translate(centerX,centerY);
            ctx.rotate(angle + arc/2);
            ctx.textAlign = "right";
            ctx.fillStyle = "#fff";
            ctx.font = `${Math.floor(radius/10)}px Arial`;
            ctx.fillText(options[i] || `옵션${i+1}`, radius - 20, 10);
            ctx.restore();
        }
    }

    function spinWheel(){
        if (spinning) return;
        spinning = true;
        const spinAngle = Math.random()*360 + 1800;
        const duration = 4000;
        const start = performance.now();
        function animate(now){
            const elapsed = now - start;
            if (elapsed < duration){
                const progress = elapsed / duration;
                const easeOut = 1 - Math.pow(1 - progress, 3);
                startAngle = (spinAngle * easeOut) * Math.PI / 180;
                drawWheel();
                requestAnimationFrame(animate);
            } else {
                spinning = false;
                startAngle = (spinAngle * Math.PI / 180) % (2*Math.PI);
                drawWheel();
                declareWinner();
            }
        }
        requestAnimationFrame(animate);
    }

    function declareWinner(){
        const arc = 2*Math.PI/optionCount;
        const pointerAngle = (3*Math.PI/2 - startAngle + 2*Math.PI) % (2*Math.PI);
        const winningIndex = Math.floor(pointerAngle / arc) % optionCount;
        const winner = options[winningIndex] || `옵션${winningIndex+1}`;
        document.getElementById("result").textContent = `당첨: ${winner}`;
    }

    // spin button
    document.getElementById("spinBtn").addEventListener("click", spinWheel);

    // 초기 inputs 및 draw
    renderInputs();
    drawWheel();
    window.addEventListener('resize', drawWheel);
});