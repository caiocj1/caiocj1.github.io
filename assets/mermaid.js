(() => {
  const diagrams = Array.from(document.querySelectorAll('.mermaid'));
  if (!diagrams.length || !window.mermaid) return;

  const sources = new Map(diagrams.map((diagram) => [diagram, diagram.textContent]));
  let renderQueue = Promise.resolve();

  const themeVariables = () => {
    const styles = getComputedStyle(document.documentElement);
    const color = (name) => styles.getPropertyValue(name).trim();
    return {
      background: color('--paper'),
      primaryColor: color('--accent-pale'),
      primaryTextColor: color('--ink'),
      primaryBorderColor: color('--accent'),
      lineColor: color('--accent-dark'),
      secondaryColor: color('--surface'),
      secondaryTextColor: color('--ink'),
      secondaryBorderColor: color('--line'),
      tertiaryColor: color('--paper-deep'),
      tertiaryTextColor: color('--ink'),
      tertiaryBorderColor: color('--line'),
      noteBkgColor: color('--surface'),
      noteTextColor: color('--ink'),
      noteBorderColor: color('--line'),
      edgeLabelBackground: color('--paper'),
      clusterBkg: color('--surface'),
      clusterBorder: color('--line'),
      fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    };
  };

  const renderDiagrams = async () => {
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: themeVariables(),
    });

    for (const diagram of diagrams) {
      diagram.textContent = sources.get(diagram);
      diagram.removeAttribute('data-processed');
      diagram.classList.remove('mermaid-error');
      try {
        await window.mermaid.run({ nodes: [diagram], suppressErrors: false });
      } catch (error) {
        diagram.textContent = sources.get(diagram);
        diagram.classList.add('mermaid-error');
        const source = diagram.closest('.mermaid-figure')?.querySelector('.mermaid-source');
        if (source) source.open = true;
        console.warn('Could not render Mermaid diagram.', error);
      }
    }
  };

  const scheduleRender = () => {
    renderQueue = renderQueue.then(renderDiagrams, renderDiagrams);
  };

  scheduleRender();
  window.addEventListener('themechange', scheduleRender);
})();
