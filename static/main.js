let page = 1;
let loading = false;
let allLoaded = false;
let currentQuery = '';

const tbody = document.getElementById('items-body');
const searchInput = document.getElementById('search-input');

function loadItems(reset = false) {
    if (loading || allLoaded) return;

    loading = true;
    document.getElementById('loading').style.display = 'block';

    fetch(`/list?page=${page}&q=${encodeURIComponent(currentQuery)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(res => res.json())
        .then(data => {
            if (reset) tbody.innerHTML = '';

            if (data.length === 0) {
                allLoaded = true;
                tbody.innerHTML =
                    '<tr><td colspan="5">No items found.</td></tr>';
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
            document.getElementById('loading').style.display = 'none';
        });
}

/* Infinite scroll */
window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
        loadItems();
    }
});

/* Live search */
searchInput?.addEventListener('input', () => {
    currentQuery = searchInput.value;
    page = 1;
    allLoaded = false;
    loadItems(true);
});

/* Initial load */
if (tbody) {
    loadItems();
}
