const form = document.getElementById('prediction-form');
const seatingInput = document.getElementById('seating-no');
const scoreInput = document.getElementById('score');
const submitButton = document.getElementById('predict-button');
const errorBox = document.getElementById('form-error');
const loadingState = document.getElementById('loading-state');
const resultSection = document.getElementById('prediction-result');
const totalDegree = Number(document.body.dataset.totalDegree) || 320;

const bandMeta = {
    strong: {
        title: 'فرصة قوية',
        description: 'درجتك أعلى من المؤشر المتوقع.',
    },
    close: {
        title: 'منافسة قريبة',
        description: 'أنت قريب من الحد المتوقع.',
    },
    stretch: {
        title: 'اختيار طموح',
        description: 'الفارق صغير؛ احتفظ بها في رغباتك.',
    },
};

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function formatNumber(value) {
    return new Intl.NumberFormat('ar-EG').format(value);
}

function helpTip(text) {
    const safeText = escapeHtml(text);
    return `
        <span
            class="help-tip"
            tabindex="0"
            aria-label="${safeText}"
            data-tooltip="${safeText}"
        >؟</span>
    `;
}

function normalizeNumericInput(value) {
    const arabicDigits = '٠١٢٣٤٥٦٧٨٩';
    return String(value)
        .trim()
        .replace(/[٠-٩]/g, digit => arabicDigits.indexOf(digit))
        .replace(/[٫,]/g, '.');
}

function selectedMode() {
    return form.querySelector('input[name="input_mode"]:checked').value;
}

function syncInputMode({ focus = false } = {}) {
    const mode = selectedMode();
    document.querySelectorAll('[data-input-panel]').forEach(panel => {
        const isActive = panel.dataset.inputPanel === mode;
        panel.hidden = !isActive;
        panel.querySelector('input').disabled = !isActive;
    });
    if (focus) {
        (mode === 'seating' ? seatingInput : scoreInput).focus();
    }
    clearError();
}

function showError(message, target) {
    errorBox.textContent = message;
    errorBox.hidden = false;
    errorBox.focus();
    if (target) {
        target.setAttribute('aria-invalid', 'true');
    }
}

function clearError() {
    errorBox.textContent = '';
    errorBox.hidden = true;
    seatingInput.removeAttribute('aria-invalid');
    scoreInput.removeAttribute('aria-invalid');
}

function setLoading(isLoading) {
    loadingState.hidden = !isLoading;
    submitButton.disabled = isLoading;
    submitButton.querySelector('span:first-child').textContent = isLoading
        ? 'جارٍ حساب التوقع'
        : 'اعرض الكليات المتوقعة';
}

function renderCollege(college) {
    const margin = college.score_margin >= 0
        ? `+${college.score_margin}`
        : college.score_margin;
    const marginMeaning = college.score_margin >= 0
        ? `درجتك أعلى من مؤشر هذه الكلية بـ ${college.score_margin} درجة.`
        : `درجتك أقل من مؤشر هذه الكلية بـ ${Math.abs(college.score_margin)} درجة.`;
    const indicatorMeaning =
        `بدأنا بحد 2025 وهو ${college.cutoff_2025}، وكان عند ترتيب يقارب ` +
        `${formatNumber(college.rank_equivalent_2025)}. الدرجة عند نفس الترتيب ` +
        `في نتائج 2026 هي ${college.predicted_cutoff_2026}.`;
    const aptitude = college.requires_aptitude
        ? '<span class="aptitude-flag">قدرات</span>'
        : '';

    return `
        <li class="college-row">
            <div class="college-copy">
                <small>${escapeHtml(college.sector_label)} ${aptitude}</small>
                <h4>${escapeHtml(college.name)}</h4>
            </div>
            <div class="college-numbers">
                <span>
                    <small>
                        مؤشر 2026
                        ${helpTip(indicatorMeaning)}
                    </small>
                    <strong>${college.predicted_cutoff_2026}</strong>
                </span>
                <span>
                    <small>
                        فارقك
                        ${helpTip(`${marginMeaning} الفارق = مجموعك ناقص مؤشر 2026.`)}
                    </small>
                    <strong class="${college.score_margin >= 0 ? 'positive' : 'negative'}">${margin}</strong>
                </span>
            </div>
            <small class="last-year">
                تنسيق 2025 الرسمي: ${college.cutoff_2025}
                ${helpTip('الحد الأدنى الرسمي المنشور لهذه الكلية في تنسيق 2025، وهو نقطة البداية للحساب.')}
            </small>
        </li>
    `;
}

function renderBands(prediction) {
    const container = document.getElementById('prediction-bands');
    container.innerHTML = ['strong', 'close', 'stretch'].map((band, index) => {
        const colleges = prediction.bands[band];
        const total = prediction.available_counts[band];
        const list = colleges.length
            ? `<ol>${colleges.map(renderCollege).join('')}</ol>`
            : '<p class="empty-band">لا توجد اختيارات في هذا النطاق.</p>';
        const limitNote = total > colleges.length
            ? `<small class="result-limit">نعرض أقرب ${colleges.length} من أصل ${formatNumber(total)} اختيارًا في هذا النطاق.</small>`
            : '';
        const countMeaning = total > colleges.length
            ? `إجمالي الكليات والاختيارات التي وقعت في هذا النطاق. نعرض أقرب ${colleges.length} منها فقط لتسهيل القراءة.`
            : 'إجمالي الكليات والاختيارات التي وقعت في هذا النطاق.';

        return `
            <details class="band band-${band}" ${index === 0 ? 'open' : ''}>
                <summary>
                    <span class="band-title">
                        <i aria-hidden="true"></i>
                        <strong>${bandMeta[band].title}</strong>
                        <small>${bandMeta[band].description}</small>
                    </span>
                    <span class="band-count">
                        <strong>${formatNumber(total)}</strong>
                        <small>اختيارًا</small>
                        ${helpTip(countMeaning)}
                    </span>
                </summary>
                <div class="band-content">
                    ${list}
                    ${limitNote}
                </div>
            </details>
        `;
    }).join('');
}

function renderResult(data) {
    const student = data.student;
    const ranking = data.ranking;
    const prediction = data.prediction;
    const isManual = data.input_mode === 'score';
    const rankText = ranking.rank_start === ranking.rank_end
        ? `حوالي المركز ${formatNumber(ranking.rank_start)}`
        : `من ${formatNumber(ranking.rank_start)} إلى ${formatNumber(ranking.rank_end)}`;

    document.getElementById('student-context').textContent =
        isManual ? 'حساب مباشر بالمجموع' : 'نتيجة الطالب';
    document.getElementById('student-name').textContent =
        isManual ? `${prediction.track_label} — مجموع ${student['الدرجة']}` : student['الاسم'];
    document.getElementById('student-meta').textContent =
        isManual ? 'بدون رقم جلوس' : `رقم الجلوس ${student['رقم الجلوس']}`;
    document.getElementById('student-score').textContent = student['الدرجة'];
    document.getElementById('student-percentage').textContent =
        `${((student['الدرجة'] / totalDegree) * 100).toFixed(2)}%`;
    document.getElementById('student-rank').textContent = rankText;
    document.getElementById('rank-note').textContent = ranking.tied_students
        ? `${formatNumber(ranking.tied_students)} طالبًا على الدرجة نفسها · ${ranking.note}`
        : ranking.note;
    document.getElementById('track-summary').textContent =
        `${prediction.track_label} · ${
            prediction.institution_filter === 'universities'
                ? 'كليات فقط'
                : 'كليات ومعاهد'
        }`;

    document.getElementById('cohort-size').textContent =
        formatNumber(ranking.total_students);
    document.getElementById('reference-count').textContent =
        formatNumber(prediction.method.reference_entries);
    document.getElementById('method-explanation').textContent =
        prediction.method.explanation;
    document.getElementById('prediction-disclaimer').textContent =
        data.disclaimer;
    document.getElementById('source-links').innerHTML = `
        <a href="${escapeHtml(prediction.sources.scientific_cutoffs)}" target="_blank" rel="noopener">تنسيق علمي 2025 الرسمي</a>
        <a href="${escapeHtml(prediction.sources.literary_cutoffs)}" target="_blank" rel="noopener">تنسيق أدبي 2025 الرسمي</a>
    `;

    renderBands(prediction);
    resultSection.hidden = false;
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildRequest() {
    const mode = selectedMode();
    const track = form.querySelector('input[name="track"]:checked');
    if (!track) {
        showError('اختر الشعبة: علمي علوم أو علمي رياضة أو أدبي.');
        return null;
    }

    const params = new URLSearchParams({
        input_mode: mode,
        track: track.value,
        institution_filter: document.getElementById('include-institutes').checked
            ? 'all'
            : 'universities',
    });

    if (mode === 'seating') {
        const seatingNo = normalizeNumericInput(seatingInput.value);
        if (!/^\d+$/.test(seatingNo)) {
            showError('اكتب رقم الجلوس بالأرقام فقط.', seatingInput);
            return null;
        }
        seatingInput.value = seatingNo;
        params.set('seating_no', seatingNo);
    } else {
        const score = normalizeNumericInput(scoreInput.value);
        if (!/^\d+(\.\d{1,2})?$/.test(score) || Number(score) < 160 || Number(score) > 320) {
            showError('اكتب مجموعًا صحيحًا من 160 إلى 320.', scoreInput);
            return null;
        }
        scoreInput.value = score;
        params.set('score', score);
    }

    return params;
}

async function requestPrediction(params) {
    const response = await fetch(`/api/predict?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'تعذر حساب التوقع الآن. حاول مرة أخرى.');
    }
    return data;
}

form.addEventListener('submit', async event => {
    event.preventDefault();
    clearError();
    resultSection.hidden = true;
    const params = buildRequest();
    if (!params) {
        return;
    }

    setLoading(true);
    try {
        renderResult(await requestPrediction(params));
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
});

form.querySelectorAll('input[name="input_mode"]').forEach(input => {
    input.addEventListener('change', () => syncInputMode({ focus: true }));
});

document.addEventListener('click', event => {
    const tip = event.target.closest('.help-tip');
    if (!tip) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    tip.focus();
});

const initialParams = new URLSearchParams(window.location.search);
const initialScore = initialParams.get('score');
const initialSeatingNo = initialParams.get('seating_no');
if (initialScore) {
    form.querySelector('input[name="input_mode"][value="score"]').checked = true;
    scoreInput.value = normalizeNumericInput(initialScore);
} else if (initialSeatingNo) {
    seatingInput.value = normalizeNumericInput(initialSeatingNo);
}
syncInputMode();
