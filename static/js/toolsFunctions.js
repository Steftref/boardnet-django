function showTool(tool, event) {
    let view = document.getElementById("toolView");

    document.querySelectorAll(".tool-card").forEach(el => el.classList.remove("active"));
    event.currentTarget.classList.add("active");

    if (tool === "dice") {
        view.innerHTML = `
            <h2>Dice</h2>
            <div id="dice" style="font-size:80px; font-family:'Cinzel',serif; color:#4a2a08;">—</div>
            <button onclick="rollDice()">Roll</button>
        `;
    }

    if (tool === "random") {
        view.innerHTML = `
            <h2>Random number</h2>
            <input id="min" placeholder="Min">
            <input id="max" placeholder="Max">
            <button onclick="generate()">Generate</button>
            <p id="result"></p>
        `;
    }

    if (tool === "picker") {
        view.innerHTML = `
           <h2>Player picker</h2>

            <input id="playerInput" placeholder="Enter name">
            <button onclick="addPlayer()">Add</button>

            <ul id="playerList" style="text-align:left;"></ul>

            <div class="roulette-container">
                <div class="roulette-pointer"></div>
                <canvas id="rouletteCanvas" width="300" height="300"></canvas>
            </div>

            <button onclick="spinRoulette()">SPIN</button>

            <p id="picked"></p>

        `;
        setTimeout(drawRoulette, 50);
    }

    if (tool === "timer") {
        view.innerHTML = `
            <h2>Timer / Stopwatch</h2>

        <input id="minutes" placeholder="Minutes (optional)">
        <input id="seconds" placeholder="Seconds (optional)">

        <button onclick="startTimer()">Start</button>
        <button onclick="stopTimer()">Stop</button>

        <h1 id="count" style="font-size:50px;">00:00:00</h1>
        `;
    }
}



function generate() {
    let minInput = document.getElementById("min").value.trim();
    let maxInput = document.getElementById("max").value.trim();

    let min = minInput === "" ? 0 : parseInt(minInput);
    let max = maxInput === "" ? Number.MAX_SAFE_INTEGER : parseInt(maxInput);

    let res = Math.floor(Math.random() * (max - min + 1)) + min;
    document.getElementById("result").innerText = "Result: " + res;
}



function rollDice() {
    const dice = document.getElementById("dice");

    let rolls = 10;
    let interval = setInterval(() => {
        dice.innerText = Math.floor(Math.random() * 6) + 1;
        rolls--;
        if (rolls === 0) {
            clearInterval(interval);
        }
    }, 100);
}







let timerInterval;
let mode = "stopwatch"; // or "countdown"

function startTimer() {
    let min = parseInt(document.getElementById("minutes").value) || 0;
    let sec = parseInt(document.getElementById("seconds").value) || 0;

    let display = document.getElementById("count");

    clearInterval(timerInterval);

    
    if (min > 0 || sec > 0) {
        mode = "countdown";
        let totalMs = (min * 60 + sec) * 1000;

        timerInterval = setInterval(() => {
            if (totalMs <= 0) {
                clearInterval(timerInterval);
                display.innerText = "TIME'S UP!";
                return;
            }

            totalMs -= 10;

            let minutes = Math.floor(totalMs / 60000);
            let seconds = Math.floor((totalMs % 60000) / 1000);
            let ms = totalMs % 1000;

            display.innerText =
                String(minutes).padStart(2, '0') + ":" +
                String(seconds).padStart(2, '0') + ":" +
                String(ms).padStart(3, '0');

        }, 10);

    } else {
        
        mode = "stopwatch";
        let totalMs = 0;

        timerInterval = setInterval(() => {
            totalMs += 10;

            let minutes = Math.floor(totalMs / 60000);
            let seconds = Math.floor((totalMs % 60000) / 1000);
            let ms = totalMs % 1000;

            display.innerText =
                String(minutes).padStart(2, '0') + ":" +
                String(seconds).padStart(2, '0') + ":" +
                String(ms).padStart(3, '0');

        }, 10);
    }
}

function stopTimer() {
    clearInterval(timerInterval);
}

let players = [];
let rotation = 0;

const colors = [
    "#e74c3c", "#3498db", "#2ecc71", "#f1c40f",
    "#9b59b6", "#1abc9c", "#e67e22", "#34495e"
];

function addPlayer() {
    let input = document.getElementById("playerInput");
    if (!input.value) return;

    players.push(input.value);
    input.value = "";

    renderPlayerList();
    drawRoulette();
}
function removePlayer(index) {
    players.splice(index, 1);
    renderPlayerList();
    drawRoulette();
}

function renderPlayerList() {
    let list = document.getElementById("playerList");
    list.innerHTML = "";

    players.forEach((name, index) => {
        let li = document.createElement("li");
        li.innerText = name;

        let removeBtn = document.createElement("span");
        removeBtn.innerText = " ✕";
        removeBtn.className = "remove-player";
        removeBtn.onclick = () => removePlayer(index);

        li.appendChild(removeBtn);
        list.appendChild(li);
    });
}


function drawRoulette() {
    let canvas = document.getElementById("rouletteCanvas");
    if (!canvas) return;

    let ctx = canvas.getContext("2d");
    let center = canvas.width / 2;
    let radius = center;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (players.length === 0) {
        ctx.beginPath();
        ctx.arc(center, center, radius, 0, Math.PI * 2);
        ctx.fillStyle = "#eee";
        ctx.fill();
        ctx.fillStyle = "#333";
        ctx.textAlign = "center";
        ctx.fillText("Add players", center, center);
        return;
    }

    let angle = (Math.PI * 2) / players.length;

    for (let i = 0; i < players.length; i++) {
        let start = i * angle;

        
        ctx.beginPath();
        ctx.moveTo(center, center);
        ctx.arc(center, center, radius, start, start + angle);
        ctx.fillStyle = colors[i % colors.length];
        ctx.fill();

        
        ctx.save();
        ctx.translate(center, center);
        ctx.rotate(start + angle / 2);
        ctx.textAlign = "right";
        ctx.fillStyle = "#fff";
        ctx.font = "bold 14px Georgia";
        ctx.fillText(players[i], radius - 10, 5);
        ctx.restore();
    }

    
    ctx.beginPath();
    ctx.arc(center, center, 30, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
}

function spinRoulette() {
    if (players.length === 0) return;

    let canvas = document.getElementById("rouletteCanvas");
    let result = document.getElementById("picked");

    let spins = 20 + Math.floor(Math.random() * 20);
    let step = 10;
    let speed = 20;
    let interval = setInterval(() => {
        rotation += speed;
        speed *= 0.97;

        canvas.style.transform = `rotate(${rotation}deg)`;

        if (speed < 0.5) {
            clearInterval(interval);

            let slice = 360 / players.length;
            let pointer = 270;
            let normalized = ((pointer - rotation) % 360 + 360) % 360;
            let selectedIndex = Math.floor(normalized / slice);

            result.innerText = "Selected: " + players[selectedIndex];
        }
    }, 30);
}