from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = 'http://127.0.0.1:5000'
DESKTOP_SCREENSHOT = Path('/tmp/thanawya-prediction-desktop.png')
MOBILE_SCREENSHOT = Path('/tmp/thanawya-prediction-mobile.png')


def assert_no_horizontal_overflow(page):
    dimensions = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth
        })"""
    )
    assert dimensions['scrollWidth'] <= dimensions['clientWidth'], dimensions


def assert_skip_link_is_hidden(page):
    state = page.locator('.skip-link').evaluate(
        """element => ({
            opacity: getComputedStyle(element).opacity,
            focused: document.activeElement === element
        })"""
    )
    assert state == {'opacity': '0', 'focused': False}, state


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    desktop = browser.new_page(viewport={'width': 1440, 'height': 1000})
    console_errors = []
    desktop.on(
        'console',
        lambda message: (
            console_errors.append(message.text)
            if message.type == 'error'
            else None
        ),
    )

    desktop.goto(f'{BASE_URL}/predict')
    desktop.wait_for_load_state('networkidle')
    assert desktop.get_by_role('heading', name='اعرف أقرب كلياتك').is_visible()
    assert desktop.get_by_role('textbox', name='رقم الجلوس').is_visible()
    assert_no_horizontal_overflow(desktop)

    desktop.get_by_text('المجموع مباشرة', exact=True).click()
    desktop.get_by_role('textbox', name='المجموع').fill('290')
    desktop.get_by_text('علمي علوم', exact=True).click()
    desktop.get_by_role('button', name='اعرض الكليات المتوقعة').click()
    desktop.locator('#prediction-result').wait_for(state='visible')
    assert desktop.locator('#student-name').inner_text() == 'علمي علوم — مجموع 290'
    assert desktop.locator('#student-score').inner_text() == '290'
    assert desktop.get_by_text('فرصة قوية', exact=True).is_visible()
    assert desktop.get_by_text('منافسة قريبة', exact=True).is_visible()
    assert desktop.get_by_text('اختيار طموح', exact=True).is_visible()
    assert desktop.locator('.college-row:visible').count() > 0
    assert desktop.locator('.band-count').first.inner_text().endswith('اختيارًا\n؟')
    assert desktop.get_by_text('كيف حسبنا مؤشر 2026؟', exact=True).is_visible()
    assert desktop.locator(
        '.college-row:visible .help-tip[aria-label*="بدأنا بحد 2025"]'
    ).first.is_visible()
    assert desktop.locator(
        '.college-row:visible .help-tip[aria-label*="الفارق = مجموعك"]'
    ).first.is_visible()
    count_tip = desktop.locator('.band-strong .band-count .help-tip')
    count_tip.click()
    assert desktop.locator('.band-strong').get_attribute('open') == ''
    desktop.wait_for_timeout(200)
    assert count_tip.evaluate(
        "element => getComputedStyle(element, '::after').opacity"
    ) == '1'
    desktop.get_by_text('الأرقام دي جاية منين؟', exact=True).click()
    assert desktop.locator('#reference-count').inner_text() == '١٬٦٩٩'
    assert_no_horizontal_overflow(desktop)
    assert_skip_link_is_hidden(desktop)
    desktop.screenshot(path=DESKTOP_SCREENSHOT, full_page=True)

    desktop.goto(BASE_URL)
    desktop.wait_for_load_state('networkidle')
    desktop.locator('#query').fill('2001970')
    desktop.locator('#search-button').click()
    desktop.locator('.prediction-link').wait_for(state='visible')
    desktop.locator('.prediction-link').click()
    desktop.wait_for_load_state('networkidle')
    assert desktop.locator('#seating-no').input_value() == '2001970'

    mobile = browser.new_page(
        viewport={'width': 390, 'height': 844},
        device_scale_factor=1,
        is_mobile=True,
        has_touch=True,
    )
    mobile.goto(f'{BASE_URL}/predict?seating_no=2001970')
    mobile.wait_for_load_state('networkidle')
    assert mobile.locator('#seating-no').input_value() == '2001970'
    assert_no_horizontal_overflow(mobile)
    mobile.get_by_text('علمي رياضة', exact=True).click()
    mobile.get_by_role('button', name='اعرض الكليات المتوقعة').click()
    mobile.locator('#prediction-result').wait_for(state='visible')
    assert mobile.locator('#student-name').inner_text() == 'احمد محمود السيد عبدالجواد السيد'
    assert mobile.locator('.college-row:visible').count() > 0
    assert_no_horizontal_overflow(mobile)
    assert_skip_link_is_hidden(mobile)
    mobile.screenshot(path=MOBILE_SCREENSHOT, full_page=True)

    assert not console_errors, console_errors
    browser.close()

print(f'desktop_screenshot={DESKTOP_SCREENSHOT}')
print(f'mobile_screenshot={MOBILE_SCREENSHOT}')
