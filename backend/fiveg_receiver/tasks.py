from celery import shared_task, chain
from datetime import datetime

from api.mongodb import get_collection, get_era_key
from api.metrics import SPECTRUM_RECEIVED_TOTAL, CELERY_TASK_DURATION
import diffusion_solver.tasks
import anomaly_detector.tasks

import time

_ERA_BY_ARTIFACT = {
    '红山文化': 'neolithic_hongshan',
    '良渚文化': 'neolithic_liangzhu',
}


def _get_era_for_artifact(artifact_id: str) -> str:
    idx = int(artifact_id.replace('JD', '')) if artifact_id.startswith('JD') else 0
    if idx <= 100:
        return 'neolithic_hongshan'
    return 'neolithic_liangzhu'


@shared_task
def receive_spectrum(artifact_id, device_id, spectrum_type, spectrum_data, wavelengths, energies):
    t0 = time.time()
    timestamp = datetime.now()
    era = _get_era_for_artifact(artifact_id)

    if spectrum_type == 'raman':
        collection = get_collection('raman_spectrum')
    else:
        collection = get_collection('xrf_spectrum')

    doc = {
        'artifact_id': artifact_id,
        'device_id': device_id,
        'timestamp': timestamp,
        'era': era,
        'spectrum_data': spectrum_data,
        'wavelengths': wavelengths,
        'energies': energies,
    }
    collection.insert_one(doc)

    spectrum_coll = get_collection('spectrum_data')
    spectrum_coll.insert_one({
        'artifact_id': artifact_id,
        'device_id': device_id,
        'type': spectrum_type,
        'timestamp': timestamp,
        'era': era,
    })

    SPECTRUM_RECEIVED_TOTAL.labels(spectrum_type=spectrum_type, device_id=device_id).inc()

    chain(
        diffusion_solver.tasks.solve_diffusion.si(artifact_id),
        anomaly_detector.tasks.detect_anomaly.si(artifact_id),
    ).apply_async()

    CELERY_TASK_DURATION.labels(task_name='receive_spectrum').observe(time.time() - t0)
    return {'status': 'received', 'artifact_id': artifact_id}
