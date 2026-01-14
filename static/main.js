/* =========================================================
   LIST PAGE (UNCHANGED)
   ========================================================= */

let page = 1;
let loading = false;
let allLoaded = false;
let currentQuery = '';

const tbody = document.getElementById('items-body');
const searchInput = document.getElementById('search-input');

function loadItems(reset = false) {
    if (loading || allLoaded) return;

    loading = true;
    document.getElementById('loading')?.style && (document.getElementById('loading').style.display = 'block');

    fetch(`/list?page=${page}&q=${encodeURIComponent(currentQuery)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(res => res.json())
        .then(data => {
            if (reset && tbody) tbody.innerHTML = '';

            if (!tbody || data.length === 0) {
                allLoaded = true;
                return;
            }

            data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.name}</td>
                    <td>${item.rarity}</td>
                    <td>${item.stattrak}</td>
                    <td>${item.souvenir}</td>
                    <td>${item.image ? `<img src="${item.image}" class="weapon-img">` : 'No Image'}</td>
                `;
                tbody.appendChild(tr);
            });

            page++;
        })
        .finally(() => {
            loading = false;
            document.getElementById('loading')?.style && (document.getElementById('loading').style.display = 'none');
        });
}

window.addEventListener('scroll', () => {
    if (tbody && window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
        loadItems();
    }
});

searchInput?.addEventListener('input', () => {
    currentQuery = searchInput.value;
    page = 1;
    allLoaded = false;
    loadItems(true);
});

if (tbody) loadItems();
