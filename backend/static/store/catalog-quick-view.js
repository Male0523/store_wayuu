(() => {
  const dialog = document.querySelector('.quick-view');
  if (!dialog) return;
  const image = dialog.querySelector('.quick-view-image img');
  const title = dialog.querySelector('#quick-view-title');
  const region = dialog.querySelector('.quick-region');
  const description = dialog.querySelector('.quick-description');
  const details = dialog.querySelector('.quick-details');
  const size = dialog.querySelector('.quick-size');
  const price = dialog.querySelector('.quick-price');
  const link = dialog.querySelector('.quick-link');
  const addForm = dialog.querySelector('.quick-add-form');
  document.querySelectorAll('.manta-photo').forEach((cardLink) => cardLink.addEventListener('click', (event) => {
    event.preventDefault();
    const card = cardLink.closest('.manta-card');
    const cardImage = cardLink.querySelector('img');
    image.src = cardImage?.src || '';
    image.alt = cardImage?.alt || '';
    title.textContent = card.querySelector('h3')?.textContent.trim() || 'Manta Wayuu';
    region.textContent = card.querySelector('.manta-region')?.textContent.trim() || 'La Guajira';
    description.textContent = card.querySelector('.full-description')?.textContent.trim() || '';
    details.innerHTML = card.querySelector('.quick-data dl')?.innerHTML || '';
    size.textContent = card.querySelector('.size-tag')?.textContent.trim() || '';
    price.textContent = card.querySelector('footer strong')?.textContent.trim() || '';
    link.href = cardLink.href;
    if (addForm) {
      addForm.action = cardLink.dataset.addUrl || '';
      const button = addForm.querySelector('button');
      const available = Number(cardLink.dataset.stock || 0);
      button.disabled = available < 1;
      button.textContent = available < 1 ? 'Manta agotada' : 'Agregar al carrito';
    }
    dialog.showModal();
  }));
  dialog.querySelector('.quick-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
})();
