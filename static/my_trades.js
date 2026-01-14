document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("my-trades-list");
  if (!container) return;

  fetch("/api/my_trades")
    .then(res => res.json())
    .then(trades => {
      if (!trades.length) {
        container.innerHTML = "<p>You have no trades.</p>";
        return;
      }

      trades.forEach(trade => {
        const card = document.createElement("div");
        card.className = "trade-card";

        card.innerHTML = `
          <div class="trade-header">
            <span>${formatTradeTime(trade.time)}</span>
            <button class="delete-btn">Delete</button>
          </div>

          <div class="trade-grids">

            <div class="trade-side">
              <h3>has</h3>
              <div class="item-grid">
                ${renderGrid(trade.has)}
              </div>
            </div>

            <div class="trade-side">
              <h3>wants</h3>
              <div class="item-grid">
                ${renderGrid(trade.wants)}
              </div>
            </div>

          </div>
        `;


        card.querySelector(".delete-btn").addEventListener("click", () => {
          if (!confirm("Delete this trade?")) return;

          fetch("/api/delete_trade", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ trade_id: trade.trade_id })
          })
          .then(res => res.json())
          .then(data => {
            if (data.success) card.remove();
          });
        });

        container.appendChild(card);
      });
    });
});
function formatTradeTime(isoTime) {
  const now = new Date();
  const then = new Date(isoTime);
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }

  if (diffSeconds < 3600) {
    return `${Math.floor(diffSeconds / 60)}m ago`;
  }

  if (diffSeconds < 86400) {
    return `${Math.floor(diffSeconds / 3600)}h ago`;
  }

  return then.toISOString().split("T")[0];
}

function renderGrid(items) {
  const slots = [];

  for (let i = 0; i < 10; i++) {
    const item = items[i];

    if (item) {
      slots.push(`
        <div class="item-slot">
          ${item.image ? `<img src="${item.image}" alt="${item.name}">` : ""}
          <div class="item-tooltip">
            ${item.name}
          </div>
        </div>
      `);
    } else {
      slots.push(`<div class="item-slot empty"></div>`);
    }
  }

  return slots.join("");
}
