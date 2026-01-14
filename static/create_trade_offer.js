/* =========================================================
   CREATE TRADE OFFER (ITEM GRID + DRAG + SUBMIT)
   ========================================================= */
console.log("CTO: file loaded");

document.addEventListener("DOMContentLoaded", () => {
    console.log("CTO: DOMContentLoaded fired");

    const searchInput = document.getElementById("item-search");
    const scrollBox = document.getElementById("trade-results-scroll");
    const grid = document.getElementById("trade-results-grid");
    const hasGrid = document.getElementById("has-grid");
    const wantsGrid = document.getElementById("wants-grid");
    const submitBtn = document.querySelector(".trade-submit button");

    if (!searchInput || !scrollBox || !grid || !hasGrid || !wantsGrid || !submitBtn) return;
    console.log("CTO: guard passed");

    let tradePage = 1;
    let tradeLoading = false;
    let tradeAllLoaded = false;
    let tradeQuery = "";
    let dragSource = null; // "search" | "slot"

    const hasItems = new Set();    // ITEM IDS
    const wantsItems = new Set();  // ITEM IDS

    let draggedItem = null;
    let draggedFromSlot = null;
    let droppedOnTarget = false;

    /* ---------- helpers ---------- */

    function updateSubmitState() {
        submitBtn.disabled = !(hasItems.size > 0 && wantsItems.size > 0);
    }

    function firstEmptySlot(gridEl) {
        return gridEl.querySelector(".item-slot.empty");
    }

    function fillSlot(slot, item) {
        slot.classList.remove("empty");
        slot.dataset.item = item.id;
        slot.innerHTML = `
            <div class="slot-content" draggable="true">
                ${item.image ? `<img src="${item.image}">` : ""}
                <div class="slot-name">${item.name}</div>
            </div>
        `;
    }

    function clearSlot(slot) {
        slot.classList.add("empty");
        slot.innerHTML = "";
        slot.removeAttribute("data-item");
    }

    /* ---------- load trade items ---------- */
    console.log("CTO: about to fetch /list", tradePage, tradeQuery);

    function loadTradeItems(reset = false) {
        console.log("CTO: loadTradeItems called", { reset });

        if (tradeLoading || tradeAllLoaded) return;

        if (reset) {
            tradePage = 1;
            tradeAllLoaded = false;
            grid.innerHTML = "";
            scrollBox.scrollTop = 0;
        }

        tradeLoading = true;

        fetch(`/list?page=${tradePage}&q=${encodeURIComponent(tradeQuery)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
            .then(res => res.json())
            .then(items => {
                if (!items.length) {
                    tradeAllLoaded = true;
                    return;
                }

                items.forEach(item => {
                    const tile = document.createElement("div");
                    tile.className = "search-item";
                    tile.draggable = true;
                    tile.dataset.id = item.id;
                    tile.dataset.name = item.name;
                    tile.innerHTML = `
                        ${item.image ? `<img src="${item.image}">` : ""}
                        <div>${item.name}</div>
                    `;
                    grid.appendChild(tile);
                });

                tradePage++;

                requestAnimationFrame(() => {
                    if (scrollBox.scrollHeight <= scrollBox.clientHeight && !tradeAllLoaded) {
                        loadTradeItems(false);
                    }
                });
            })
            .finally(() => tradeLoading = false);
    }

    scrollBox.addEventListener("scroll", () => {
        if (scrollBox.scrollTop + scrollBox.clientHeight >= scrollBox.scrollHeight - 80) {
            loadTradeItems(false);
        }
    });

    searchInput.addEventListener("input", () => {
        tradeQuery = searchInput.value.trim();
        tradeAllLoaded = false;
        loadTradeItems(true);
    });
    loadTradeItems(true);
    /* ---------- drag logic ---------- */

    grid.addEventListener("dragstart", e => {
        e.stopPropagation();
        const tile = e.target.closest(".search-item");
        if (!tile) return;

        draggedItem = {
            id: tile.dataset.id,
            name: tile.dataset.name,
            image: tile.querySelector("img")?.src || ""
        };

        dragSource = "search";
        draggedFromSlot = null;
        droppedOnTarget = false;
    });

    document.addEventListener("dragstart", e => {
        if (e.target.closest(".search-item")) return;

        const content = e.target.closest(".slot-content");
        if (!content) return;


        const slot = content.closest(".item-slot");
        if (!slot) return;

        draggedFromSlot = slot;
        draggedItem = {
            id: slot.dataset.item,
            name: content.querySelector(".slot-name").textContent,
            image: content.querySelector("img")?.src || ""
        };

        dragSource = "slot";
        droppedOnTarget = false;
    });

    function attachDropTarget(gridEl, side) {
        gridEl.addEventListener("dragover", e => {
            e.preventDefault();
            gridEl.classList.add("drag-over");
        });

        gridEl.addEventListener("dragleave", () => {
            gridEl.classList.remove("drag-over");
        });

        gridEl.addEventListener("drop", e => {
            e.preventDefault();
            gridEl.classList.remove("drag-over");
            if (!draggedItem) return;

            droppedOnTarget = true;
            const set = side === "has" ? hasItems : wantsItems;

            if (set.has(draggedItem.id) || set.size >= 10) return;

            const empty = firstEmptySlot(gridEl);
            if (!empty) return;

            set.add(draggedItem.id);
            fillSlot(empty, draggedItem);

            if (dragSource === "slot" && draggedFromSlot) {
                const oldSet =
                    draggedFromSlot.dataset.side === "has"
                        ? hasItems
                        : wantsItems;

                oldSet.delete(draggedItem.id);
                clearSlot(draggedFromSlot);
            }


            updateSubmitState();
            draggedFromSlot = null;
        });
    }


    attachDropTarget(hasGrid, "has");
    attachDropTarget(wantsGrid, "wants");

    document.addEventListener("dragend", () => {
        if (draggedFromSlot && !droppedOnTarget) {
            const set = draggedFromSlot.dataset.side === "has" ? hasItems : wantsItems;
            set.delete(draggedFromSlot.dataset.item);
            clearSlot(draggedFromSlot);
            updateSubmitState();
        }

        draggedItem = null;
        draggedFromSlot = null;
        droppedOnTarget = false;
        dragSource = null;
    });

    /* ---------- submit ---------- */

    submitBtn.addEventListener("click", () => {
        fetch("/api/create_trade_offer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                has: Array.from(hasItems),
                wants: Array.from(wantsItems)
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert("Trade created!");
                    window.location.href = "/";
                } else {
                    alert(data.error || "Failed to create trade");
                }
            });
    });
});