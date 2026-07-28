let currentPage = 1;
let currentQuery = '';
let totalResults = 0;
const perPage = 10;
const totalDegree = Number(document.body.dataset.totalDegree) || 320;

function performSearch() {
    const query = document.getElementById('query').value;
    if (!query) return;

    currentQuery = query;
    currentPage = 1;
    document.getElementById('results').innerHTML = '';
    fetchResults();
}

function loadMore() {
    currentPage++;
    fetchResults();
}

async function fetchResults() {
    const resultsContainer = document.getElementById('results');
    const loading = document.getElementById('loading');
    const loadMoreBtn = document.getElementById('load-more');
    const resetBtn = document.getElementById('reset-button');

    loading.style.display = 'block';
    loadMoreBtn.style.display = 'none';
    resetBtn.style.display = 'none';

    const response = await fetch(`/search?query=${currentQuery}&page=${currentPage}`);
    const data = await response.json();
    
    loading.style.display = 'none';
    
    if (data.error) {
        resultsContainer.innerHTML = `<p style="text-align: center;">${data.error}</p>`;
    } else {
        if (currentPage === 1 && data.results.length === 0) {
            resultsContainer.innerHTML = `<p style="text-align: center;">لا توجد نتائج لهذا البحث</p>`;
        }
        
        totalResults = data.total_results;
        
        const newResultsHtml = data.results.map(r => `
            <div class="result ${r.student_case_desc.includes('ناجح') ? 'success' : 'failure'}">
                <p><strong>الاسم:</strong> ${r['الاسم']}</p>
                <p><strong>رقم الجلوس:</strong> ${r['رقم الجلوس']}</p>
                <p><strong>الدرجة:</strong> ${r['الدرجة']} | <strong>النسبة:</strong> ${(r['الدرجة'] / totalDegree * 100).toFixed(2)}%</p>
                <p><strong>الحالة:</strong> ${r.student_case_desc}</p>
                ${r.student_case_desc.includes('ناجح') ? `<a class="prediction-link" href="/predict?seating_no=${encodeURIComponent(r['رقم الجلوس'])}">توقع الكليات المناسبة ←</a>` : ''}
            </div>
        `).join('');

        resultsContainer.innerHTML += newResultsHtml;
        
        const totalLoaded = currentPage * perPage;
        if (totalResults > totalLoaded) {
            loadMoreBtn.style.display = 'block';
            resetBtn.style.display = 'inline-block';
        } else {
            loadMoreBtn.style.display = 'none';
            if (data.results.length > 0) {
                resetBtn.style.display = 'inline-block';
            }
        }
    }
}
