"""Build the static admission reference used by the local predictor.

The official coordination pages are saved locally before running this script so
production builds never depend on an external website being available.
"""

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


MEDICAL_KEYWORDS = (
    'طب ',
    'طب الأسنان',
    'طب اسنان',
    'طب وجراحة',
    'صيدلة',
    'علاج طبيعي',
    'تمريض',
    'فني صحي',
    'العلوم الصحية',
)
ENGINEERING_KEYWORDS = (
    'هندسة',
    'تخطيط عمراني',
    'فنون جميلة (عمارة)',
)
COMPUTING_KEYWORDS = (
    'حاسبات',
    'حاسب',
    'ذكاء إصطناعي',
    'ذكاء اصطناعي',
    'علوم البيانات',
)
APTITUDE_KEYWORDS = (
    'فنون جميلة',
    'فنون تطبيقية',
    'تربية فنية',
    'تربية موسيقية',
    'تربية رياضية',
    'علوم الرياضة',
)
INSTITUTE_KEYWORDS = (
    'معهد',
    'المعهد',
    'العالي',
    'العالى',
    'أكاديمية',
    'اكاديمية',
    'الأكاديمية',
    'الفني ',
    'الفنى ',
)


class CutoffTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current_row = []
        elif tag in {'td', 'th'} and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in {'td', 'th'} and self.current_cell is not None:
            value = ' '.join(''.join(self.current_cell).split())
            self.current_row.append(value)
            self.current_cell = None
        elif tag == 'tr' and self.current_row is not None:
            if len(self.current_row) == 2:
                self.rows.append(self.current_row)
            self.current_row = None


def parse_cutoff_table(html_file):
    parser = CutoffTableParser()
    parser.feed(Path(html_file).read_text(encoding='utf-8-sig'))
    records = []
    for name, cutoff in parser.rows:
        try:
            numeric_cutoff = float(cutoff)
        except ValueError:
            continue
        records.append({
            'name': name.strip(),
            'cutoff_2025': numeric_cutoff,
        })
    return pd.DataFrame(records)


def classify_scientific_track(name):
    if any(keyword in name for keyword in MEDICAL_KEYWORDS):
        return ['science']
    if any(keyword in name for keyword in ENGINEERING_KEYWORDS):
        return ['math']
    if any(keyword in name for keyword in COMPUTING_KEYWORDS):
        if ' رياضة' in name:
            return ['math']
        if ' علوم' in name:
            return ['science']
    if name.endswith(' رياضة'):
        return ['math']
    if name.endswith(' علوم'):
        return ['science']
    return ['science', 'math']


def classify_sector(name):
    if any(keyword in name for keyword in MEDICAL_KEYWORDS):
        return 'medical'
    if any(keyword in name for keyword in ENGINEERING_KEYWORDS):
        return 'engineering'
    if any(keyword in name for keyword in COMPUTING_KEYWORDS):
        return 'computing'
    if (
        'اقتصاد و علوم سياسية' in name
        or 'اقتصادية و العلوم السياسية' in name
        or 'سياسة واقتصاد' in name
    ):
        return 'economics'
    if 'ألسن' in name or 'لغات' in name or 'ترجمة' in name:
        return 'languages'
    if 'إعلام' in name or 'اعلام' in name:
        return 'media'
    if 'زراعة' in name:
        return 'agriculture'
    if 'فنون' in name or 'آثار' in name or 'اثار' in name:
        return 'arts'
    if 'تربية' in name:
        return 'education'
    if 'تجارة' in name or 'إدارة' in name or 'ادارة' in name:
        return 'commerce'
    if 'حقوق' in name:
        return 'law'
    if 'سياحة' in name or 'فنادق' in name:
        return 'tourism'
    if 'خدمة اجتماعية' in name or 'خدمه اجتماعيه' in name:
        return 'social'
    if 'علوم' in name:
        return 'science'
    return 'other'


def build_rank_lookup(results_file):
    scores = pd.read_excel(
        results_file,
        usecols=['total_degree'],
    )['total_degree']
    scores = scores[scores.between(0, 320)]
    counts = scores.value_counts().sort_index(ascending=False)
    cumulative = counts.cumsum()
    return counts, cumulative


def rank_at_cutoff(cumulative, cutoff):
    matching_scores = cumulative.index[cumulative.index >= cutoff]
    if matching_scores.empty:
        return 0
    return int(cumulative.loc[matching_scores[-1]])


def prepare_record(row, track, cumulative):
    name = row['name']
    cutoff = float(row['cutoff_2025'])
    tracks = [track] if track == 'literary' else classify_scientific_track(name)
    return {
        'name': name,
        'cutoff_2025': cutoff,
        'rank_equivalent_2025': rank_at_cutoff(cumulative, cutoff),
        'tracks': tracks,
        'sector': classify_sector(name),
        'institution_type': (
            'institute'
            if any(keyword in name for keyword in INSTITUTE_KEYWORDS)
            else 'university'
        ),
        'requires_aptitude': any(
            keyword in name for keyword in APTITUDE_KEYWORDS
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--science-html', required=True)
    parser.add_argument('--literary-html', required=True)
    parser.add_argument('--results-2025', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    science = parse_cutoff_table(args.science_html)
    literary = parse_cutoff_table(args.literary_html)
    counts, cumulative = build_rank_lookup(args.results_2025)

    colleges = [
        prepare_record(row, 'scientific', cumulative)
        for _, row in science.iterrows()
    ]
    colleges.extend(
        prepare_record(row, 'literary', cumulative)
        for _, row in literary.iterrows()
    )

    payload = {
        'version': 1,
        'baseline_year': 2025,
        'target_year': 2026,
        'total_degree': 320,
        'method': 'rank-equivalent cutoff mapping',
        'sources': {
            'scientific_cutoffs': (
                'https://tansik.digital.gov.eg/Application/Certificates/'
                'Thanwy/Limits/LimitE2025.htm'
            ),
            'literary_cutoffs': (
                'https://tansik.digital.gov.eg/Application/Certificates/'
                'Thanwy/Limits/LimitA2025.htm'
            ),
        },
        'baseline_distribution': [
            {'score': float(score), 'count': int(count)}
            for score, count in counts.items()
        ],
        'colleges': colleges,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8',
    )
    print(
        f"Wrote {len(colleges):,} admission records and "
        f"{len(counts):,} score bands to {output}"
    )


if __name__ == '__main__':
    main()
