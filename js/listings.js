/* ========================================
   Whitaker Exclusives — Listings JS
   ======================================== */

async function loadListings() {
  try {
    const res = await fetch('listings.json?t=' + Date.now());
    return await res.json();
  } catch (e) {
    console.error('Failed to load listings:', e);
    return [];
  }
}

function renderListingCard(l) {
  const photo = (l.photos && l.photos.length) ? l.photos[0] : '';
  const imgHtml = photo
    ? `<img src="${photo}" alt="${l.address}" loading="lazy">`
    : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f3460,#1a1a2e)"><span style="color:#888">No Photo</span></div>`;

  return `
    <a href="listing.html?id=${l.id}" class="listing-card">
      <div class="listing-card-img">
        ${imgHtml}
        <div class="listing-card-status">${l.status === 'active' ? 'Exclusive' : l.status}</div>
      </div>
      <div class="listing-card-body">
        <div class="listing-card-price">${formatPrice(l.price)}</div>
        <div class="listing-card-address">${l.address}</div>
        <div class="listing-card-city">${l.city}, ${l.state} ${l.zip}</div>
        <div class="listing-card-details">
          <span>${l.beds} Beds</span>
          <span>${l.baths} Baths</span>
          <span>${l.sqft ? l.sqft.toLocaleString() : '—'} Sqft</span>
        </div>
        ${l.description ? `<div class="listing-card-desc">${l.description}</div>` : ''}
      </div>
    </a>`;
}

// Listings grid page
async function initListingsPage() {
  const grid = document.getElementById('listings-grid');
  if (!grid) return;

  const listings = await loadListings();
  const active = listings.filter(l => l.status === 'active');

  if (!active.length) {
    grid.innerHTML = `
      <div class="listings-empty" style="grid-column:1/-1">
        <h3>No Exclusive Listings Available</h3>
        <p>Check back soon — new exclusive properties are added regularly.</p>
      </div>`;
    return;
  }
  grid.innerHTML = active.map(renderListingCard).join('');
}

// Featured listings on homepage (show up to 3)
async function initFeaturedListings() {
  const grid = document.getElementById('featured-grid');
  if (!grid) return;

  const listings = await loadListings();
  const active = listings.filter(l => l.status === 'active').slice(0, 3);

  if (!active.length) {
    document.getElementById('featured-section')?.style.setProperty('display', 'none');
    return;
  }
  grid.innerHTML = active.map(renderListingCard).join('');
}

// Listing detail page
async function initListingDetail() {
  const container = document.getElementById('listing-detail');
  if (!container) return;

  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id) { container.innerHTML = '<p>Listing not found.</p>'; return; }

  const listings = await loadListings();
  const l = listings.find(x => x.id === id);
  if (!l) { container.innerHTML = '<p>Listing not found.</p>'; return; }

  document.title = `${l.address} — Whitaker Exclusives`;

  // Gallery
  const photos = l.photos && l.photos.length ? l.photos : [];
  let galleryHtml;
  if (photos.length) {
    galleryHtml = `<div class="listing-gallery-hero"><img src="${photos[0]}" alt="${l.address}"></div>`;
  } else {
    galleryHtml = `<div class="listing-gallery-placeholder"><span>No Photos Available</span></div>`;
  }

  // Features
  const featuresHtml = l.features && l.features.length
    ? `<div class="listing-features"><h3>Features</h3><ul>${l.features.map(f => `<li>${f}</li>`).join('')}</ul></div>`
    : '';

  // Meta info
  const metaItems = [
    l.mlsNumber && ['MLS Number', l.mlsNumber],
    l.yearBuilt && ['Year Built', l.yearBuilt],
    l.lotSize && ['Lot Size', l.lotSize],
    l.agent && ['Listing Agent', l.agent],
  ].filter(Boolean);

  const metaHtml = metaItems.length
    ? `<div class="listing-meta">${metaItems.map(([label, val]) => `<div class="listing-meta-item"><span class="listing-meta-label">${label}</span><span>${val}</span></div>`).join('')}</div>`
    : '';

  // Photo gallery (all photos)
  let allPhotosHtml = '';
  if (photos.length > 1) {
    allPhotosHtml = `
      <div style="margin-top:48px">
        <h3 style="font-family:var(--font-display);font-size:1.3rem;margin-bottom:16px">All Photos</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">
          ${photos.map((p, i) => `<img src="${p}" alt="Photo ${i+1}" style="width:100%;aspect-ratio:4/3;object-fit:cover;cursor:pointer" onclick="openGallery(${i})">`).join('')}
        </div>
      </div>`;
  }

  container.innerHTML = `
    <div class="listing-hero">${galleryHtml}</div>
    <div class="listing-detail">
      <div class="container">
        <a href="listings.html" class="back-link">← All Listings</a>
        <div class="listing-detail-grid">
          <div>
            <div class="listing-price">${formatPrice(l.price)}</div>
            <div class="listing-address">${l.address}</div>
            <div class="listing-city">${l.city}, ${l.state} ${l.zip}</div>
            <div class="listing-stats">
              <div class="listing-stat-item"><div class="listing-stat-value">${l.beds}</div><div class="listing-stat-label">Bedrooms</div></div>
              <div class="listing-stat-item"><div class="listing-stat-value">${l.baths}</div><div class="listing-stat-label">Bathrooms</div></div>
              <div class="listing-stat-item"><div class="listing-stat-value">${l.sqft ? l.sqft.toLocaleString() : '—'}</div><div class="listing-stat-label">Sq Ft</div></div>
            </div>
            <div class="listing-description">${l.description || ''}</div>
            ${featuresHtml}
            ${metaHtml}
            ${allPhotosHtml}
          </div>
          <div>
            <div class="listing-sidebar-cta">
              <h3>Interested in this property?</h3>
              <p>Contact us for a private showing of this exclusive listing.</p>
              <a href="tel:9547641447" class="btn btn-solid">Call 954-764-1447</a>
              <a href="mailto:chad@w-realty.com?subject=Inquiry: ${encodeURIComponent(l.address)}" class="btn">Email Agent</a>
              <div class="listing-sidebar-agent">
                Listed by <strong>${l.agent || 'Whitaker Realty'}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Gallery Modal -->
    <div class="gallery-modal" id="gallery-modal">
      <button class="gallery-modal-close" onclick="closeGallery()">×</button>
      <button class="gallery-modal-nav prev" onclick="galleryNav(-1)">‹</button>
      <img id="gallery-modal-img" src="" alt="">
      <button class="gallery-modal-nav next" onclick="galleryNav(1)">›</button>
    </div>`;

  // Gallery modal logic
  window._galleryPhotos = photos;
  window._galleryIdx = 0;
}

function openGallery(idx) {
  window._galleryIdx = idx;
  const modal = document.getElementById('gallery-modal');
  document.getElementById('gallery-modal-img').src = window._galleryPhotos[idx];
  modal.classList.add('active');
}
function closeGallery() { document.getElementById('gallery-modal')?.classList.remove('active'); }
function galleryNav(dir) {
  const photos = window._galleryPhotos;
  window._galleryIdx = (window._galleryIdx + dir + photos.length) % photos.length;
  document.getElementById('gallery-modal-img').src = photos[window._galleryIdx];
}

document.addEventListener('DOMContentLoaded', () => {
  initListingsPage();
  initFeaturedListings();
  initListingDetail();
});

document.addEventListener('keydown', (e) => {
  if (!document.getElementById('gallery-modal')?.classList.contains('active')) return;
  if (e.key === 'Escape') closeGallery();
  if (e.key === 'ArrowLeft') galleryNav(-1);
  if (e.key === 'ArrowRight') galleryNav(1);
});
