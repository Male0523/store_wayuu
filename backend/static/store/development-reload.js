/* Recarga solo para el servidor local de desarrollo. */
(() => {
  let version;
  const check = async () => {
    try {
      const response = await fetch('/__development-version__/', { cache: 'no-store' });
      if (!response.ok) return;
      const current = (await response.json()).version;
      if (version && current !== version) window.location.reload();
      version = current;
    } catch (_) { /* El servidor puede estar reiniciándose. */ }
  };
  check();
  window.setInterval(check, 1800);
})();
