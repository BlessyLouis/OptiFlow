/* =========================================================
   OptiFlow — Main JavaScript
   ========================================================= */

// ── Sidebar mobile toggle ────────────────────────────────
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');

if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });
  document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

// ── Global search ────────────────────────────────────────
const searchInput = document.getElementById('globalSearch');
const searchResults = document.getElementById('searchResults');

let searchTimeout = null;

if (searchInput && searchResults) {
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const q = searchInput.value.trim();

    if (q.length < 2) {
      searchResults.classList.remove('active');
      searchResults.innerHTML = '';
      return;
    }

    searchTimeout = setTimeout(async () => {
      try {
        const resp = await fetch(`/orders/api/search?q=${encodeURIComponent(q)}`);
        const data = await resp.json();

        if (data.length === 0) {
          searchResults.innerHTML = '<div class="search-result-item text-muted">No results found</div>';
        } else {
          searchResults.innerHTML = data.map(order => `
            <a href="/orders/${order.order_id}" class="search-result-item d-flex justify-content-between align-items-center text-decoration-none">
              <span>
                <span class="fw-semibold" style="font-family:monospace">${order.order_id}</span>
                <span class="text-muted ms-2">${order.customer_name}</span>
              </span>
              <span class="text-muted small">${order.current_status}</span>
            </a>
          `).join('');
        }
        searchResults.classList.add('active');
      } catch (e) {
        console.error('Search failed:', e);
      }
    }, 280);
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.classList.remove('active');
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      searchResults.classList.remove('active');
      searchInput.blur();
    }
  });
}

// ── Auto-dismiss flash alerts ─────────────────────────────
document.querySelectorAll('.alert.alert-success').forEach(el => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    bsAlert.close();
  }, 4000);
});
