from celery import shared_task, chain
from datetime import datetime

from api.mongodb import get_collection
import diffusion_solver.tasks
import anomaly_detector.tasks


@shared_task
def receive_spectrum(artifact_id, device_id, spectrum_type, spectrum_data, wavelengths, energies):
    timestamp = datetime.now()

    if spectrum_type == 'raman':
        collection = get_collection('raman_spectrum')
    else:
        collection = get_collection('xrf_spectrum')

    doc = {
        'artifact_id': artifact_id,
        'device_id': device_id,
        'timestamp': timestamp,
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
    })

    chain(
        diffusion_solver.tasks.solve_diffusion.si(artifact_id),
        anomaly_detector.tasks.detect_anomaly.si(artifact_id),
    ).apply_async()

    return {'status': 'received', 'artifact_id': artifact_id}
