from celery import shared_task
from django.conf import settings
from api.mongodb import get_collection
from api.metrics import ANOMALY_DETECTED_TOTAL, ANOMALY_FORGERY_SCORE, CELERY_TASK_DURATION
from anomaly_detector.models import AnomalyDetector
import time


_detector_instance = None


def get_detector():
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector(
            n_estimators=getattr(settings, 'ISOLATION_FOREST_N_ESTIMATORS', 50),
            max_samples=getattr(settings, 'ISOLATION_FOREST_MAX_SAMPLES', 256),
            contamination=getattr(settings, 'ISOLATION_FOREST_CONTAMINATION', 0.1),
            max_buffer_size=getattr(settings, 'ISOLATION_FOREST_MAX_BUFFER', 10000),
        )
    return _detector_instance


@shared_task
def detect_anomaly(artifact_id):
    t0 = time.time()
    from alert_ws.tasks import send_anomaly_alert

    xrf_collection = get_collection('xrf_spectrum')
    raman_collection = get_collection('raman_spectrum')

    xrf_data = xrf_collection.find_one(
        {'artifact_id': artifact_id},
        sort=[('timestamp', -1)]
    )
    raman_data = raman_collection.find_one(
        {'artifact_id': artifact_id},
        sort=[('timestamp', -1)]
    )

    detector = get_detector()
    features = detector.extract_features(xrf_data, raman_data)
    result = detector.detect(features, artifact_id)

    result_collection = get_collection('anomaly_results')
    result_collection.insert_one(result.copy())

    threshold = getattr(settings, 'ANOMALY_SCORE_THRESHOLD', 0.7)
    if result['forgery_probability'] > threshold:
        alert_data = {
            'artifact_id': artifact_id,
            'forgery_probability': result['forgery_probability'],
            'risk_level': result['risk_level'],
            'anomaly_reasons': result['anomaly_reasons'],
            'anomaly_score': result['anomaly_score'],
        }
        send_anomaly_alert.delay(alert_data)

    ANOMALY_DETECTED_TOTAL.labels(is_anomaly=str(result['is_anomaly'])).inc()
    ANOMALY_FORGERY_SCORE.labels(artifact_id=artifact_id).set(result['forgery_probability'])
    CELERY_TASK_DURATION.labels(task_name='detect_anomaly').observe(time.time() - t0)

    return result
