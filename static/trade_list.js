document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("trade-list");
  if (!container) return;

  function loadTrades(filters = {}) {
    const params = new URLSearchParams(filters);

    fetch(`/api/trades?${params.toString()}`)
      .then(res => res.json())
      .then(trades => {
        container.innerHTML = "";

        if (!trades.length) {
          container.innerHTML = "<p>No trades found.</p>";
          return;
        }

        trades.forEach(trade => {
          const card = document.createElement("div");
          card.className = "trade-card";
          card.dataset.userId = trade.user_id;

          card.innerHTML = `
            <div class="trade-header">
              <strong>${trade.username}</strong>
              <span>${formatTradeTime(trade.time)}</span>
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

            <div class="trade-actions">
              <button class="message-btn">Message</button>
            </div>
          `;

          card.querySelector(".message-btn").addEventListener("click", (e) => {
            e.stopPropagation();
            window.location.href = `/chat?user=${trade.username}`;
          });

          container.appendChild(card);
        });
      })
      .catch(err => console.error("Trade load failed:", err));
  }

  loadTrades({});

  document.getElementById("apply-filter")?.addEventListener("click", () => {
    loadTrades(getFilterParams());
  });

  document.getElementById("clear-filter")?.addEventListener("click", () => {
    document.getElementById("filter-item").value = "";
    document.getElementById("filter-type").value = "any";
    loadTrades({});
  });
});


function getFilterParams() {
    return {
        item: document.getElementById("filter-item")?.value.trim(),
        type: document.getElementById("filter-type")?.value || "any"
    };
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

  // Otherwise show date
  return then.toISOString().split("T")[0];
}
