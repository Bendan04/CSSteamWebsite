let page = 1;
let loading = false;
let allLoaded = false;
let currentQuery = '';

const tbody = document.getElementById('items-body');
const searchInput = document.getElementById('search-input');

function loadItems(reset=false) {
    if (loading || allLoaded) return;
    loading = true;
    document.getElementById('loading').style.display = 'block';

    const url = `/list?page=${page}&q=${encodeURIComponent(currentQuery)}`;

    fetch(url, { headers: {'X-Requested-With': 'XMLHttpRequest'} })
        .then(res => res.json())
        .then(data => {
            if (reset) tbody.innerHTML = '';
            if (data.length === 0) {
                allLoaded = true;
                if (reset) tbody.innerHTML = '<tr><td colspan="5">No items found.</td></tr>';
                document.getElementById('loading').innerText = 'No more items.';
                loading = false;
                return;
            }

            data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.name}</td>
                    <td>${item.rarity}</td>
                    <td>${item.stattrak}</td>
                    <td>${item.souvenir}</td>
                    <td>${item.image ? `<img src="${item.image}" alt="${item.name}" class="weapon-img">` : 'No Image'}</td>
                `;
                tbody.appendChild(tr);
            });

            page += 1;
            loading = false;
            document.getElementById('loading').style.display = 'none';
        })
        .catch(err => {
            console.error(err);
            loading = false;
            document.getElementById('loading').style.display = 'none';
        });
}

// Infinite scroll
window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
        loadItems();
    }
});

// Live search
searchInput.addEventListener('input', () => {
    currentQuery = searchInput.value;
    page = 1;
    allLoaded = false;
    loadItems(true);
});

// Initial load
loadItems();