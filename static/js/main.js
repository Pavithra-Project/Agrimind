/* ================================================
   AgriMind AI — main.js
   Full SPA navigation + all module handlers
   ================================================ */

document.addEventListener('DOMContentLoaded', () => {

    const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

    /* ─── Expose toast globally (used in HTML onclick) ────── */
    window.showToast = showToast;

    /* ══════════════════════════════════════════════════════
       SIDEBAR NAVIGATION
    ══════════════════════════════════════════════════════ */
    const navItems   = document.querySelectorAll('.nav-item');
    const views      = document.querySelectorAll('.content-view');
    const pageTitle  = document.getElementById('page-title');

    navItems.forEach(item => {
        item.addEventListener('click', e => {
            const view = item.dataset.view;
            if (!view) return; // real href links pass through

            const target = document.getElementById(`view-${view}`);
            if (!target) {
                // If it's a real link (like /profile or /dashboard), let the default click happen
                const href = item.getAttribute('href');
                if (href && href !== '#') {
                    return; // Follow href naturally
                }
                return; // Do nothing if it's # and no target
            }

            e.preventDefault();

            // activate nav
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // activate view
            views.forEach(v => v.classList.remove('active'));
            target.classList.add('active');

            // update header title
            if (pageTitle) pageTitle.textContent = item.textContent.trim();

            // Load module data
            if (view === 'dashboard') loadDashboardStats();
            if (view === 'profile') loadProfileDetails();
        });
    });

    /* ══════════════════════════════════════════════════════
       DARK MODE
    ══════════════════════════════════════════════════════ */
    const darkBtn = document.getElementById('dark-mode-toggle');
    if (darkBtn) {
        darkBtn.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
            darkBtn.innerHTML = isDark
                ? '<i class="fa-solid fa-moon"></i>'
                : '<i class="fa-solid fa-sun"></i>';
        });
    }

    /* ══════════════════════════════════════════════════════
       TOAST NOTIFICATIONS
    ══════════════════════════════════════════════════════ */
    function showToast(msg, type = 'success') {
        const t = document.createElement('div');
        t.className = `toast toast-${type}`;
        t.textContent = msg;
        document.body.appendChild(t);
        requestAnimationFrame(() => t.classList.add('show'));
        setTimeout(() => {
            t.classList.remove('show');
            setTimeout(() => t.remove(), 400);
        }, 3200);
    }

    /* ══════════════════════════════════════════════════════
       UI STATE HELPERS
    ══════════════════════════════════════════════════════ */
    function setLoading(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.querySelector('.spinner').style.display = 'block';
        el.querySelector('.result-data').style.display = 'none';
        el.querySelector('.result-empty').style.display = 'none';
    }

    function setResult(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.querySelector('.spinner').style.display = 'none';
        el.querySelector('.result-data').style.display = 'block';
        el.querySelector('.result-empty').style.display = 'none';
    }

    function setEmpty(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.querySelector('.spinner').style.display = 'none';
        el.querySelector('.result-data').style.display = 'none';
        el.querySelector('.result-empty').style.display = 'block';
    }

    function setText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    async function apiPost(url, data) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await resp.json();
    }

    /* ══════════════════════════════════════════════════════
       0. DASHBOARD DASHBOARD
    ══════════════════════════════════════════════════════ */
    let priceChart = null;

    async function loadDashboardStats() {
        try {
            const data = await (await fetch('/dashboard-stats')).json();
            setText('kpi-crop', data.top_crop);
            setText('kpi-profit', INR.format(data.expected_profit));
            setText('kpi-risk', data.risk_level);
            setText('kpi-analyses', data.total_analyses);
            
            setText('insight-month', data.best_month);
            setText('insight-trend', data.price_trend);

            // Chart
            const ctx = document.getElementById('dashboardPriceChart');
            if (ctx) {
                if (window.dashChart) window.dashChart.destroy();
                window.dashChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.chart_labels,
                        datasets: [{
                            label: 'Market Price (₹)',
                            data: data.chart_data,
                            borderColor: '#2D6A4F',
                            backgroundColor: 'rgba(45, 106, 79, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }
        } catch (e) { console.error('Stats load failed', e); }
    }

    loadDashboardStats(); // Initial load

    /* ══════════════════════════════════════════════════════
       1. CROP RECOMMENDATION
    ══════════════════════════════════════════════════════ */
    const cropForm = document.getElementById('crop-form');
    if (cropForm) {
        cropForm.addEventListener('submit', async e => {
            e.preventDefault();
            setLoading('crop-result');

            try {
                const data = await apiPost('/predict-crop', {
                    soil_type:   document.getElementById('soil_type').value,
                    season:      document.getElementById('season').value,
                    temperature: document.getElementById('temperature').value,
                    humidity:    document.getElementById('humidity').value
                });

                if (data.error) throw new Error(data.error);

                setText('res-crop-conf', `AI Confidence: ${data.confidence}%`);
                setText('res-crop-name', data.crop);
                setText('res-crop-desc', data.explanation);

                setResult('crop-result');
                addActivity(`Crop analysis → <strong>${data.crop}</strong> recommended`);
                showToast('AI Recommendation Generated!', 'success');
            } catch (err) {
                showToast(err.message || 'Prediction failed', 'error');
                setEmpty('crop-result');
            }
        });
    }

    /* ══════════════════════════════════════════════════════
       2. MARKET PRICE
    ══════════════════════════════════════════════════════ */
    const priceForm = document.getElementById('price-form');
    if (priceForm) {
        priceForm.addEventListener('submit', async e => {
            e.preventDefault();
            setLoading('price-result');

            const crop = document.getElementById('price_crop').value;
            try {
                const data = await apiPost('/predict-price', {
                    crop:  crop,
                    year:  document.getElementById('price_year').value,
                    month: document.getElementById('price_month').value
                });

                const best = await (await fetch(`/best-month?crop=${crop}&current_month=${document.getElementById('price_month').value}`)).json();

                if (data.error) throw new Error(data.error);

                setText('res-price-val', INR.format(data.predicted_price));
                document.getElementById('res-price-desc').innerHTML = `
                    <p style="font-weight:600; color:var(--clr-primary); margin-bottom:.25rem;">
                        <i class="fa-solid fa-calendar-check"></i> Best month to sell: ${best.best_month}
                    </p>
                    <p style="font-size:.85rem; color:var(--clr-muted); line-height:1.5;">${best.advisory}</p>
                `;

                // Sub Chart
                const ctx = document.getElementById('priceChart');
                if (ctx) {
                    if (window.modulePriceChart) window.modulePriceChart.destroy();
                    window.modulePriceChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: ['Current', 'Avg', 'Peak'],
                            datasets: [{
                                data: [data.predicted_price, best.average_price, best.predicted_price],
                                backgroundColor: ['#1B4332', '#2D6A4F', '#95D5B2']
                            }]
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }}}
                    });
                }

                setResult('price-result');
                addActivity(`Price forecast → <strong>${crop}</strong> at ${INR.format(data.predicted_price)}`);
                showToast('Market Forecast Loaded', 'success');
            } catch (err) {
                showToast(err.message || 'Forecast failed', 'error');
                setEmpty('price-result');
            }
        });
    }

    /* ══════════════════════════════════════════════════════
       3. DISEASE DETECTION
    ══════════════════════════════════════════════════════ */
    const diseaseForm = document.getElementById('disease-form');
    const leafInput   = document.getElementById('leaf_image');
    
    if (leafInput) {
        leafInput.addEventListener('change', () => {
            const file = leafInput.files[0];
            if (file) {
                document.getElementById('file-name').textContent = file.name;
                const reader = new FileReader();
                reader.onload = e => {
                    const prev = document.getElementById('image-preview');
                    const img  = document.getElementById('preview-img');
                    img.src = e.target.result;
                    prev.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (diseaseForm) {
        diseaseForm.addEventListener('submit', async e => {
            e.preventDefault();
            const file = leafInput.files[0];
            if (!file) return showToast('Please select an image', 'error');

            setLoading('disease-result');
            const fd = new FormData();
            fd.append('file', file);

            try {
                const resp = await fetch('/detect-disease', { method: 'POST', body: fd });
                const data = await resp.json();
                if (data.error) throw new Error(data.error);

                const sevColor = { Low: '#16a34a', Medium: '#d97706', High: '#dc2626' }[data.severity] || '#4b5563';
                const sevBg    = { Low: '#D1FAE5', Medium: '#FEF3C7', High: '#FEE2E2' }[data.severity] || '#F3F4F6';

                setText('res-disease-name', data.disease);
                document.getElementById('res-disease-meta').innerHTML = `
                    <span class="confidence-badge">Confidence: ${data.confidence}%</span>
                    <span class="severity-tag" style="background:${sevBg}; color:${sevColor};">
                        ${data.severity} Risk
                    </span>
                `;
                setText('res-disease-treatment', data.treatment);
                document.getElementById('res-disease-name').style.color = sevColor;

                setResult('disease-result');
                addActivity(`Disease scan → <strong>${data.disease}</strong>`);
                showToast('Diagnosis complete', data.severity === 'High' ? 'error' : 'success');
            } catch (err) {
                showToast(err.message || 'Diagnosis error', 'error');
                setEmpty('disease-result');
            }
        });
    }

    /* ══════════════════════════════════════════════════════
       4. YIELD OPTIMIZER
    ══════════════════════════════════════════════════════ */
    const yieldForm = document.getElementById('yield-form');
    if (yieldForm) {
        yieldForm.addEventListener('submit', async e => {
            e.preventDefault();
            setLoading('yield-result');

            try {
                const data = await apiPost('/predict-yield', {
                    crop:        document.getElementById('yield_crop').value,
                    soil_type:   document.getElementById('yield_soil').value,
                    temperature: document.getElementById('yield_temp').value,
                    humidity:    document.getElementById('yield_hum').value,
                    rainfall:    document.getElementById('yield_rain').value
                });

                if (data.error) throw new Error(data.error);

                const effNum = parseInt(data.efficiency);
                setText('res-yield-perc', data.efficiency);
                setText('res-yield-impact', `Impact: ${data.impact_score}`);
                setText('res-yield-boost', `Boost: ${data.expected_improvement}`);

                const bar = document.getElementById('yield-progress');
                if (bar) {
                    bar.style.width = '0%';
                    setTimeout(() => { bar.style.width = effNum + '%'; }, 100);
                }

                const suggEl = document.getElementById('res-yield-suggestions');
                if (suggEl) {
                    suggEl.innerHTML = data.suggestions.length === 0 
                        ? '<p class="text-muted" style="text-align:center; padding:1rem;">✅ Optimal conditions!</p>'
                        : data.suggestions.map(s => `<div class="suggestion-item"><i class="fa-solid fa-lightbulb"></i>${s}</div>`).join('');
                }

                setResult('yield-result');
                addActivity(`Yield optimization → efficiency <strong>${data.efficiency}</strong>`);
                showToast(`Yield efficiency: ${data.efficiency}`, 'success');
            } catch (err) {
                showToast(err.message || 'Optimization failed', 'error');
                setEmpty('yield-result');
            }
        });
    }

    /* ══════════════════════════════════════════════════════
       5. AI CHATBOT
    ══════════════════════════════════════════════════════ */
    const chatForm    = document.getElementById('chat-form');
    const chatInput   = document.getElementById('chat-input');
    const chatMsgs    = document.getElementById('chat-messages');

    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const msg = chip.dataset.msg;
            if (!msg || !chatInput) return;
            chatInput.value = msg;
            chatForm?.dispatchEvent(new Event('submit'));
        });
    });

    if (chatForm) {
        chatForm.addEventListener('submit', async e => {
            e.preventDefault();
            const msg = chatInput.value.trim();
            if (!msg) return;

            appendMsg('user', msg);
            chatInput.value = '';
            const typingEl = addTypingIndicator();

            try {
                const data = await apiPost('/chatbot', { message: msg });
                typingEl.remove();
                appendMsg('ai', data.response || "I couldn't process that.");
            } catch {
                typingEl.remove();
                appendMsg('ai', "Error connecting to AI.");
            }
        });
    }

    function appendMsg(sender, text) {
        if (!chatMsgs) return;
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.innerHTML = text;
        chatMsgs.appendChild(div);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
    }

    function addTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
        chatMsgs.appendChild(div);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
        return div;
    }

    /* ══════════════════════════════════════════════════════
       PROFILE & HISTORY LOGIC
    ══════════════════════════════════════════════════════ */
    let userHistoryData = [];

    async function loadProfileDetails() {
        try {
            const data = await (await fetch('/profile-details')).json();
            setText('prof-display-email', data.email);
            setText('prof-email-val', data.email);
            userHistoryData = data.history || [];
            renderHistory(userHistoryData);
        } catch (err) { console.error('Profile fetch failed', err); }
    }

    function renderHistory(history) {
        const list = document.getElementById('history-list');
        if (!list) return;

        if (history.length === 0) {
            list.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 2.5rem; color: var(--clr-muted);">No searches performed yet.</td></tr>';
            return;
        }

        const typeIcons = { 'Crop Recommendation': 'fa-seedling', 'Price Prediction': 'fa-chart-line', 'Disease Detection': 'fa-stethoscope', 'Yield Optimization': 'fa-gauge-high' };
        const typeClass = { 'Crop Recommendation': 'bg-crop', 'Price Prediction': 'bg-price', 'Disease Detection': 'bg-disease', 'Yield Optimization': 'bg-yield' };

        list.innerHTML = history.map(h => {
             let inputStr = h.input;
             try {
                if (inputStr.startsWith('{')) {
                    const obj = JSON.parse(inputStr.replace(/'/g, '\"'));
                    inputStr = Object.entries(obj).map(([k,v]) => `${k}: ${v}`).join(', ');
                }
             } catch(e) {}
             
             const icon = typeIcons[h.type] || 'fa-magnifying-glass';
             const cls  = typeClass[h.type] || '';

             return `
                <tr>
                    <td><span class="type-badge ${cls}"><i class="fa-solid ${icon}"></i> ${h.type}</span></td>
                    <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${inputStr}">${inputStr}</td>
                    <td><strong>${h.result}</strong></td>
                    <td class="text-muted" style="font-size: .8rem;">${new Date(h.date).toLocaleString()}</td>
                </tr>
             `;
        }).join('');
    }

    const historyFilter = document.getElementById('history-filter');
    if (historyFilter) {
        historyFilter.addEventListener('change', () => {
             const val = historyFilter.value;
             renderHistory(val === 'all' ? userHistoryData : userHistoryData.filter(h => h.type === val));
        });
    }

    /* ══════════════════════════════════════════════════════
       RECENT ACTIVITY TRACKER
    ══════════════════════════════════════════════════════ */
    const recentList = document.getElementById('recent-list');
    function addActivity(html) {
        if (!recentList) return;
        const empty = recentList.querySelector('p');
        if (empty) empty.remove();

        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `<span class="activity-dot"></span>${html}`;
        recentList.insertBefore(item, recentList.firstChild);

        const items = recentList.querySelectorAll('.activity-item');
        if (items.length > 5) items[items.length - 1].remove();
    }

}); // DOMContentLoaded
