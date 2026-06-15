from celery import shared_task
import numpy as np
from datetime import datetime

from api.mongodb import get_collection
from django.conf import settings
from .models import DiffusionModel
from .tensor import CTCalibratedTensorBuilder

_tensor_builder = CTCalibratedTensorBuilder()


def _build_diffusion_model(artifact, use_anisotropic=True):
    culture = artifact.get('culture', '红山文化')
    jade_type = artifact.get('jade_type', '玉璧')
    texture = artifact.get('texture')

    custom_tensor = None

    if texture and texture.get('main_orientation_euler'):
        try:
            euler_deg = tuple(texture['main_orientation_euler'])
            custom_tensor = _tensor_builder.build_preset(
                jade_culture=culture,
                jade_type=jade_type,
                orientation_deg=euler_deg
            )
            if texture.get('grain_size_um'):
                gs = texture['grain_size_um']
                gb_factor = 1.0 + 0.3 * (50.0 / max(gs, 1.0))
                custom_tensor.D_parallel *= gb_factor
                custom_tensor.D_perp1 *= gb_factor * 0.9
                custom_tensor.D_perp2 *= gb_factor * 0.85
        except Exception:
            custom_tensor = None

    return DiffusionModel(
        jade_culture=culture,
        jade_type=jade_type,
        use_anisotropic=use_anisotropic,
        custom_tensor=custom_tensor
    )


@shared_task
def solve_diffusion(artifact_id, temperature=None, humidity=None, time_hours=None, use_anisotropic=True):
    artifact_coll = get_collection('jade_artifacts')
    artifact = artifact_coll.find_one({'artifact_id': artifact_id})
    if not artifact:
        return {'error': 'Artifact not found', 'artifact_id': artifact_id}

    thickness = artifact.get('size', {}).get('thickness', 2.0)
    _temperature = temperature if temperature is not None else 25
    _humidity = humidity if humidity is not None else 50
    _time_hours = time_hours if time_hours is not None else 1000

    model = _build_diffusion_model(artifact, use_anisotropic=use_anisotropic)

    fe_result = model.simulate_diffusion(
        ion_type='Fe3+',
        thickness_mm=thickness,
        time_hours=_time_hours,
        temperature=_temperature,
        humidity=_humidity
    )

    mn_result = model.simulate_diffusion(
        ion_type='Mn2+',
        thickness_mm=thickness,
        time_hours=_time_hours,
        temperature=_temperature,
        humidity=_humidity
    )

    penetration_depth_fe = model.calculate_penetration_depth(
        np.array(fe_result['concentration_profile']), thickness
    )
    penetration_depth_mn = model.calculate_penetration_depth(
        np.array(mn_result['concentration_profile']), thickness
    )

    tensor_info = model.get_tensor_info()

    result = {
        'artifact_id': artifact_id,
        'timestamp': datetime.now(),
        'fe3_diffusion': fe_result,
        'mn2_diffusion': mn_result,
        'penetration_depth_fe_mm': float(penetration_depth_fe),
        'penetration_depth_mn_mm': float(penetration_depth_mn),
        'max_penetration_mm': max(float(penetration_depth_fe), float(penetration_depth_mn)),
        'penetration_isotropic_fe_mm': fe_result.get(
            'penetration_depth_isotropic_mm', penetration_depth_fe
        ),
        'penetration_isotropic_mn_mm': mn_result.get(
            'penetration_depth_isotropic_mm', penetration_depth_mn
        ),
        'temperature': _temperature,
        'humidity': _humidity,
        'simulation_time_hours': _time_hours,
        'solver_mode': fe_result.get('solver_mode', 'unknown'),
        'tensor_info': tensor_info
    }

    results_coll = get_collection('diffusion_results')
    results_coll.insert_one(result)
    result['_id'] = str(result['_id'])

    if result['max_penetration_mm'] > settings.DIFFUSION_ALERT_THRESHOLD_MM:
        alert_data = {
            'artifact_id': artifact_id,
            'alert_type': 'diffusion',
            'severity': 'warning',
            'message': (
                f'沁色深度超过阈值: 各向异性 {result["max_penetration_mm"]:.2f}mm'
                f' (均质模式 ~{max(
                    result["penetration_isotropic_fe_mm"],
                    result["penetration_isotropic_mn_mm"]
                ):.2f}mm，差异 '
                f'{100 * (result["max_penetration_mm"] / max(
                    result["penetration_isotropic_fe_mm"],
                    result["penetration_isotropic_mn_mm"]
                ) - 1):.1f}%)'
            ),
            'data': {
                'penetration_mm': result['max_penetration_mm'],
                'solver': result['solver_mode'],
                'tensor_info': tensor_info
            },
            'timestamp': datetime.now(),
            'status': 'active'
        }
        from alert_ws.tasks import send_diffusion_alert
        send_diffusion_alert.delay(alert_data)

    return result


@shared_task
def solve_tensor_comparison(artifact_id, temperature, humidity, time_hours):
    artifact_coll = get_collection('jade_artifacts')
    artifact = artifact_coll.find_one({'artifact_id': artifact_id})
    if not artifact:
        return {'error': 'Artifact not found', 'artifact_id': artifact_id}

    thickness = artifact.get('size', {}).get('thickness', 2.0)

    model_aniso = _build_diffusion_model(artifact, use_anisotropic=True)

    compare_fe = model_aniso.compare_isotropic_vs_anisotropic(
        'Fe3+', thickness, time_hours, temperature
    )
    compare_mn = model_aniso.compare_isotropic_vs_anisotropic(
        'Mn2+', thickness, time_hours, temperature
    )

    temp_sens = model_aniso.temperature_sensitivity_analysis(
        'Fe3+', (5, 40), thickness, time_hours
    )

    threshold = settings.DIFFUSION_ALERT_THRESHOLD_MM

    summary = {
        'aniso_enhancement_fe_pct': compare_fe['comparison']['relative_error_percent'],
        'aniso_enhancement_mn_pct': compare_mn['comparison']['relative_error_percent'],
        'alert_threshold_mm': threshold,
        'alert_cases': {
            'iso_triggered': (
                compare_fe['isotropic']['depth_mm'] > threshold
                or compare_mn['isotropic']['depth_mm'] > threshold
            ),
            'aniso_triggered': (
                compare_fe['anisotropic']['depth_mm'] > threshold
                or compare_mn['anisotropic']['depth_mm'] > threshold
            ),
            'discrepancy': (
                compare_fe['comparison']['alert_discrepancy']
                or compare_mn['comparison']['alert_discrepancy']
            )
        }
    }

    return {
        'artifact_id': artifact_id,
        'conditions': {
            'thickness_mm': thickness,
            'time_hours': time_hours,
            'temperature_c': temperature,
            'humidity_pct': humidity
        },
        'Fe3_comparison': compare_fe,
        'Mn2_comparison': compare_mn,
        'temperature_sensitivity_Fe3': temp_sens,
        'alert_summary': summary
    }
