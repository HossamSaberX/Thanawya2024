import os
import sys
from pathlib import Path


os.environ.setdefault('CACHE_TYPE', 'SimpleCache')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app  # noqa: E402


def request_prediction(client, track, institution_filter='universities'):
    response = client.get(
        '/api/predict',
        query_string={
            'seating_no': '2001970',
            'track': track,
            'institution_filter': institution_filter,
        },
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def request_score_prediction(
    client,
    score,
    track,
    institution_filter='universities',
):
    response = client.get(
        '/api/predict',
        query_string={
            'input_mode': 'score',
            'score': score,
            'track': track,
            'institution_filter': institution_filter,
        },
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def all_colleges(payload):
    return [
        college
        for colleges in payload['prediction']['bands'].values()
        for college in colleges
    ]


with app.test_client() as client:
    assert client.get('/predict').status_code == 200
    assert client.get(
        '/api/predict',
        query_string={'seating_no': 'not-a-number', 'track': 'science'},
    ).status_code == 400
    assert client.get(
        '/api/predict',
        query_string={'seating_no': '99999999', 'track': 'science'},
    ).status_code == 404
    for invalid_score in ('159.5', '320.1', '290.001', 'not-a-score'):
        response = client.get(
            '/api/predict',
            query_string={
                'input_mode': 'score',
                'score': invalid_score,
                'track': 'science',
            },
        )
        assert response.status_code == 400, response.get_json()

    search_response = client.get('/search', query_string={'query': '2001970'})
    assert search_response.status_code == 200
    assert search_response.get_json()['results'][0]['الدرجة'] == 290

    science = request_prediction(client, 'science')
    assert science['ranking']['total_students'] == 919396
    assert science['student']['الدرجة'] == 290
    assert all(
        college['institution_type'] == 'university'
        for college in all_colleges(science)
    )
    assert all(
        college['sector'] != 'engineering'
        for college in all_colleges(science)
    )

    mathematics = request_prediction(client, 'math')
    assert any(
        college['sector'] == 'engineering'
        for college in all_colleges(mathematics)
    )

    literary = request_prediction(client, 'literary', 'all')
    assert literary['prediction']['track_label'] == 'أدبي'
    assert all(
        literary['prediction']['available_counts'][band] >= len(colleges)
        for band, colleges in literary['prediction']['bands'].items()
    )

    manual = request_score_prediction(client, '290', 'science')
    assert manual['input_mode'] == 'score'
    assert manual['student']['رقم الجلوس'] is None
    assert manual['student']['الدرجة'] == 290
    assert manual['ranking']['rank_start'] == science['ranking']['rank_start']
    assert manual['prediction']['method']['reference_entries'] == 1699
    assert all(
        college['rank_equivalent_2025'] > 0
        for college in all_colleges(manual)
    )

    between_bands = request_score_prediction(client, '289.75', 'math')
    assert between_bands['ranking']['tied_students'] == 0
    assert between_bands['ranking']['rank_start'] == between_bands['ranking']['rank_end']

print('prediction_api_checks=passed')
