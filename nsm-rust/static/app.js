// NSM Processor — client-side logic

// Re-initialise Plotly scatter and track preview after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function(evt) {
  const target = evt.detail.target;
  // If the pp-root or its parent was swapped, re-init the postprocessing plot
  if (target.id === 'tab-content' || target.id === 'pp-root' ||
      (target.querySelector && target.querySelector('#scatter-plot'))) {
    setTimeout(initPostprocessingPlots, 80);
  }
});

function initPostprocessingPlots() {
  const dataEl = document.getElementById('scatter-data-json');
  const trajEl = document.getElementById('trajectory-data-json');

  if (dataEl && document.getElementById('scatter-plot')) {
    try {
      const pd = JSON.parse(dataEl.textContent);
      Plotly.newPlot('scatter-plot', pd.data, pd.layout, {
        modeBarButtonsToAdd: ['lasso2d', 'select2d'],
        displayModeBar: true,
        responsive: true,
      });

      document.getElementById('scatter-plot').on('plotly_selected', function(evt) {
        if (!evt || !evt.points) return;
        const idx = evt.points.map(p => Array.isArray(p.customdata) ? p.customdata[0] : p.customdata);
        const indEl  = document.getElementById('sel-indices');
        const cntEl  = document.getElementById('sel-count');
        if (indEl) indEl.value = JSON.stringify(idx);
        if (cntEl) cntEl.textContent = idx.length + ' selected';
        document.querySelectorAll('.sel-action').forEach(b => b.disabled = idx.length === 0);
      });
    } catch(e) { console.error('Scatter plot init failed:', e); }
  }

  if (trajEl && document.getElementById('track-preview')) {
    try {
      const trajs = JSON.parse(trajEl.textContent);
      renderTrackPreview(trajs, 'track-preview');
    } catch(e) { console.error('Track preview init failed:', e); }
  }
}

function renderTrackPreview(trajs, divId) {
  if (!trajs || !trajs.length) return;
  const groups = {};
  trajs.forEach(t => { (groups[t.kymo_key] = groups[t.kymo_key] || []).push(t); });
  const key = Object.keys(groups)[0];
  const traces = (groups[key] || []).map(t => ({
    x: t.frames, y: t.positions,
    mode: 'lines', type: 'scatter',
    line: {
      color: (t.state === 'auto-excluded' || t.state === 'manual-excluded') ? '#f38ba8' : '#89b4fa',
      width: t.state.includes('excluded') ? 2 : 1,
    },
    name: '#' + t.index,
    showlegend: t.state.includes('excluded'),
  }));
  Plotly.newPlot(divId, traces, {
    height: 280, margin: {l:40,r:20,t:20,b:40},
    paper_bgcolor: '#181825', plot_bgcolor: '#181825',
    font: {color: '#cdd6f4', size: 10},
    yaxis: {autorange: 'reversed', title: 'Position (px)'},
    xaxis: {title: 'Frame'},
    showlegend: true,
  }, {responsive: true});
}

// Used by postprocessing buttons
window.sendOverride = function(action) {
  const jobInput = document.querySelector('[name=job_id]');
  const jobId    = jobInput ? jobInput.value : '';
  const indEl    = document.getElementById('sel-indices');
  const indices  = JSON.parse((indEl ? indEl.value : null) || '[]');

  fetch('/postprocessing/override', {
    method:  'POST',
    headers: {'Content-Type': 'application/json', 'HX-Request': 'true'},
    body:    JSON.stringify({job_id: jobId, indices, action}),
  })
  .then(r => r.text())
  .then(html => {
    const root = document.getElementById('pp-root');
    if (root) {
      root.outerHTML = html;
      setTimeout(initPostprocessingPlots, 80);
    }
  });
};

window.acceptAndSave = function() {
  const jobInput = document.querySelector('[name=job_id]');
  const jobId    = jobInput ? jobInput.value : '';
  const calToggle = document.getElementById('ioc-cal-toggle');
  const fd = new FormData();
  fd.append('job_id', jobId);
  if (calToggle && calToggle.checked) fd.append('ioc_cal', 'on');

  fetch('/postprocessing/accept', {
    method: 'POST', body: fd, headers: {'HX-Request': 'true'},
  })
  .then(r => r.text())
  .then(html => {
    const el = document.getElementById('accept-result');
    if (el) el.innerHTML = html;
  });
};

// Initialise on first page load
document.addEventListener('DOMContentLoaded', function() {
  initPostprocessingPlots();
});
