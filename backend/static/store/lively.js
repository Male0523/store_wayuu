(() => {
  const header = document.querySelector('.site-header');
  const updateHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 12);
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  const targets = document.querySelectorAll('.benefit-row, .title-row, .pro-card, .pro-story, .steps article, .pro-faq, .pro-contact, .product-pro, .detail-story');
  targets.forEach((element) => element.classList.add('js-reveal'));
  if (!('IntersectionObserver' in window)) {
    targets.forEach((element) => element.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  targets.forEach((element) => observer.observe(element));
})();
