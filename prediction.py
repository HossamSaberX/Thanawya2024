import json
from bisect import bisect_left
from pathlib import Path


REFERENCE_FILE = Path(__file__).parent / 'data' / 'admission_reference_2025.json'

TRACK_LABELS = {
    'science': 'علمي علوم',
    'math': 'علمي رياضة',
    'literary': 'أدبي',
}

SECTOR_LABELS = {
    'medical': 'القطاع الطبي',
    'engineering': 'الهندسة والتخطيط',
    'computing': 'الحاسبات والذكاء الاصطناعي',
    'science': 'العلوم',
    'economics': 'الاقتصاد والعلوم السياسية',
    'languages': 'الألسن واللغات',
    'media': 'الإعلام',
    'arts': 'الفنون والآثار',
    'education': 'التربية',
    'commerce': 'التجارة والإدارة',
    'law': 'الحقوق',
    'agriculture': 'الزراعة',
    'tourism': 'السياحة والفنادق',
    'social': 'الخدمة الاجتماعية',
    'other': 'كليات ومعاهد أخرى',
}

BAND_LABELS = {
    'strong': 'فرصة قوية',
    'close': 'منافسة قريبة',
    'stretch': 'اختيار طموح',
}


class PredictionEngine:
    def __init__(self, reference_file=REFERENCE_FILE):
        with Path(reference_file).open(encoding='utf-8') as reference:
            self.reference = json.load(reference)
        self.colleges = self.reference['colleges']

    @staticmethod
    def _confidence_for_cutoff(predicted_cutoff):
        if predicted_cutoff >= 280:
            return 'high'
        if predicted_cutoff >= 220:
            return 'medium'
        return 'exploratory'

    @staticmethod
    def _band_for_delta(delta):
        if delta >= 2:
            return 'strong'
        if delta >= -1:
            return 'close'
        if delta >= -4:
            return 'stretch'
        return None

    @staticmethod
    def _projected_cutoff(rank_equivalent, rank_ends, scores):
        index = bisect_left(rank_ends, rank_equivalent)
        if index >= len(scores):
            return scores[-1]
        return scores[index]

    def predict(
        self,
        score,
        track,
        current_distribution,
        institution_filter='universities',
        limit_per_band=8,
    ):
        rank_ends = [row['rank_end'] for row in current_distribution]
        scores = [row['degree'] for row in current_distribution]
        projected_by_rank = {}
        grouped = {band: [] for band in BAND_LABELS}
        available_counts = {band: 0 for band in BAND_LABELS}

        for college in self.colleges:
            if track not in college['tracks']:
                continue
            if (
                institution_filter == 'universities'
                and college['institution_type'] != 'university'
            ):
                continue

            rank_equivalent = college['rank_equivalent_2025']
            if rank_equivalent not in projected_by_rank:
                projected_by_rank[rank_equivalent] = self._projected_cutoff(
                    rank_equivalent,
                    rank_ends,
                    scores,
                )

            predicted_cutoff = projected_by_rank[rank_equivalent]
            delta = round(score - predicted_cutoff, 1)
            band = self._band_for_delta(delta)
            if not band:
                continue

            available_counts[band] += 1
            grouped[band].append({
                'name': college['name'],
                'sector': college['sector'],
                'sector_label': SECTOR_LABELS[college['sector']],
                'institution_type': college['institution_type'],
                'requires_aptitude': college['requires_aptitude'],
                'cutoff_2025': college['cutoff_2025'],
                'rank_equivalent_2025': rank_equivalent,
                'predicted_cutoff_2026': predicted_cutoff,
                'score_margin': delta,
                'band': band,
                'band_label': BAND_LABELS[band],
                'model_confidence': self._confidence_for_cutoff(
                    predicted_cutoff
                ),
            })

        for band in grouped:
            grouped[band].sort(
                key=lambda college: (
                    -college['predicted_cutoff_2026'],
                    college['name'],
                )
            )
            grouped[band] = grouped[band][:limit_per_band]

        return {
            'track': track,
            'track_label': TRACK_LABELS[track],
            'institution_filter': institution_filter,
            'bands': grouped,
            'available_counts': available_counts,
            'method': {
                'baseline_year': self.reference['baseline_year'],
                'target_year': self.reference['target_year'],
                'name': self.reference['method'],
                'reference_entries': len(self.colleges),
                'baseline_score_bands': len(
                    self.reference['baseline_distribution']
                ),
                'explanation': (
                    'نحوّل الحد الأدنى الرسمي لعام 2025 إلى مركز ترتيبي، '
                    'ثم نبحث عن الدرجة التي تشغل المركز نفسه في توزيع 2026.'
                ),
            },
            'sources': self.reference['sources'],
        }
