let charChart = null;

function pct(x) {
  return (x * 100).toFixed(2) + "%";
}

function drawLineChart(data) {
  const ctx = document.getElementById("charChart").getContext("2d");
  if (charChart) charChart.destroy();

  charChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map(p => p.x),
      datasets: [{
        label: "Current Limited (%)",
        data: data.map(p => p.y * 100),
        borderWidth: 2,
        tension: 0.25
      }]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: "Pulls" } },
        y: {
          min: 0,
          max: 100,
          title: { display: true, text: "Probability (%)" },
          ticks: { callback: v => v + "%" }
        }
      }
    }
  });
}

async function simulate() {
  const pity6 = Number(document.getElementById("pity6").value);
  const pity120 = Number(document.getElementById("pity120").value);
  const rolls = Number(document.getElementById("rolls").value);

  const res = await fetch("http://localhost:8000/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pity_6: pity6, pity_120: pity120, rolls })
  });

  const data = await res.json();

  document.getElementById("pCur").innerText = pct(data.p_current_limited);
  document.getElementById("pOff").innerText = pct(data.p_off);
  document.getElementById("pOther").innerText = pct(data.p_other_limited);
  document.getElementById("min6").innerText = String(data.min_6star);
  document.getElementById("e5").innerText = Number(data.e_5star).toFixed(2);

  const resSeries = await fetch("http://localhost:8000/series", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pity_6: pity6, pity_120: pity120, rolls })
  });

  const seriesData = await resSeries.json();
  drawLineChart(seriesData.character);
}
