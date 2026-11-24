(() => {
  const bases={de:'index.de.html',es:'index.es.html',en:'index.html'};
  const requested=new URLSearchParams(location.search).get('lang');
  const lang=requested||(location.pathname.endsWith('/heat-overlap.html')?navigator.language.slice(0,2):document.documentElement.lang);
  const hash=location.hash;
  const book=/^#account-(original|5|6)$/.exec(hash);
  const file=Object.hasOwn(bases,lang)?bases[lang]:bases.en;
  const target=hash==='#historia' ? 'heat-archive'+(lang==='en'?'.en':'')+'.html#historia'
    : file+'#panic-paper'+(book?'-'+book[1]:'');
  location.replace(new URL(target, document.querySelector('link[rel=canonical]').href).href);
})();
