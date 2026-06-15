import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import warnings

from .tensor import (
    DiffusionTensor,
    CTCalibratedTensorBuilder,
    AnisotropicDiffusionSolver,
    get_default_tensor
)


def erf(x):
    x = np.asarray(x, dtype=float)
    sign = np.ones_like(x)
    sign[x < 0] = -1
    x_abs = np.abs(x)

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    t = 1.0 / (1.0 + p * x_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x_abs * x_abs)

    return sign * y


def erfc(x):
    return 1.0 - erf(x)


@dataclass
class DiffusionParams:
    D0: float
    activation_energy: float
    surface_concentration: float
    molar_mass: float


class DiffusionModel:

    _PARAMS = {
        'Fe3+': DiffusionParams(
            D0=5.0e-10,
            activation_energy=25.0,
            surface_concentration=0.08,
            molar_mass=55.845
        ),
        'Mn2+': DiffusionParams(
            D0=2.0e-10,
            activation_energy=28.0,
            surface_concentration=0.05,
            molar_mass=54.938
        ),
        'Cu2+': DiffusionParams(
            D0=3.5e-10,
            activation_energy=26.0,
            surface_concentration=0.03,
            molar_mass=63.546
        )
    }

    R = 8.314

    def __init__(
        self,
        jade_culture: str = '红山文化',
        jade_type: str = '玉璧',
        use_anisotropic: bool = True,
        custom_tensor: Optional[DiffusionTensor] = None,
        ct_volume: Optional[np.ndarray] = None,
        ct_voxel_um: float = 50.0
    ):
        self.use_anisotropic = use_anisotropic
        self.jade_culture = jade_culture
        self.jade_type = jade_type
        self._tensor_builder = CTCalibratedTensorBuilder()

        if custom_tensor is not None:
            self.diffusion_tensor = custom_tensor
            self._tensor_source = 'custom'
        elif ct_volume is not None:
            self.diffusion_tensor = self._tensor_builder.build_from_ct_scan(
                ct_volume, ct_voxel_um, '和田玉'
            )
            self._tensor_source = 'ct_calibrated'
        elif use_anisotropic:
            self.diffusion_tensor = get_default_tensor(jade_culture, jade_type)
            self._tensor_source = 'preset'
        else:
            self.diffusion_tensor = None
            self._tensor_source = 'isotropic'

    def get_tensor_info(self) -> Dict:
        if self.diffusion_tensor is None:
            return {
                'source': 'isotropic (homogeneous)',
                'description': '经典菲克定律，均质扩散假设'
            }

        tensor = self.diffusion_tensor
        D_matrix = tensor.get_tensor_matrix()

        return {
            'source': self._tensor_source,
            'jade_culture': self.jade_culture,
            'jade_type': self.jade_type,
            'anisotropy_ratio': round(tensor.anisotropy_ratio, 3),
            'D_parallel_m2s': tensor.D_parallel,
            'D_perp1_m2s': tensor.D_perp1,
            'D_perp2_m2s': tensor.D_perp2,
            'D_matrix_3x3': D_matrix.tolist(),
            'principal_axes': tensor.principal_axes.tolist()
        }

    def calculate_diffusion_coefficient(
        self,
        ion_type: str,
        temperature_c: float,
        humidity: float = 50.0,
        direction: Optional[np.ndarray] = None
    ) -> float:
        params = self._PARAMS.get(ion_type)
        if not params:
            raise ValueError(f"未知离子类型: {ion_type}")

        T = temperature_c + 273.15
        D_bulk = params.D0 * np.exp(-params.activation_energy * 1000 / (self.R * T))
        humidity_factor = 0.5 + 0.5 * (humidity / 100.0)
        D_bulk *= humidity_factor

        if not self.use_anisotropic or self.diffusion_tensor is None:
            return D_bulk

        if direction is None:
            direction = np.array([0, 0, 1])

        ref_D = (self.diffusion_tensor.D_parallel +
                 self.diffusion_tensor.D_perp1 +
                 self.diffusion_tensor.D_perp2) / 3.0

        scale_factor = D_bulk / ref_D if ref_D > 0 else 1.0

        temp_adjusted_tensor = DiffusionTensor(
            D_parallel=self.diffusion_tensor.D_parallel * scale_factor,
            D_perp1=self.diffusion_tensor.D_perp1 * scale_factor,
            D_perp2=self.diffusion_tensor.D_perp2 * scale_factor,
            orientation_matrix=self.diffusion_tensor.orientation_matrix,
            principal_axes=self.diffusion_tensor.principal_axes
        )

        return temp_adjusted_tensor.get_effective_diffusivity(direction)

    def get_directional_diffusivity_map(
        self,
        ion_type: str,
        temperature_c: float,
        humidity: float = 50.0,
        n_angles: int = 36
    ) -> Dict:
        if not self.use_anisotropic or self.diffusion_tensor is None:
            D_iso = self.calculate_diffusion_coefficient(ion_type, temperature_c, humidity)
            angles = np.linspace(0, 360, n_angles)
            return {
                'angles_deg': angles.tolist(),
                'diffusivities': [D_iso] * n_angles,
                'max_direction_deg': 0,
                'min_direction_deg': 0,
                'max_min_ratio': 1.0
            }

        angles = np.linspace(0, 360, n_angles)
        diffusivities = []

        for theta_deg in angles:
            theta = np.radians(theta_deg)
            direction = np.array([np.sin(theta), 0, np.cos(theta)])
            D = self.calculate_diffusion_coefficient(
                ion_type, temperature_c, humidity, direction
            )
            diffusivities.append(D)

        diffusivities = np.array(diffusivities)
        max_idx = np.argmax(diffusivities)
        min_idx = np.argmin(diffusivities)
        ratio = diffusivities[max_idx] / (diffusivities[min_idx] + 1e-20)

        return {
            'angles_deg': angles.tolist(),
            'diffusivities': diffusivities.tolist(),
            'max_direction_deg': float(angles[max_idx]),
            'min_direction_deg': float(angles[min_idx]),
            'max_min_ratio': float(ratio)
        }

    def analytical_solution(
        self,
        D: float,
        C0: float,
        x: np.ndarray,
        t: float
    ) -> np.ndarray:
        if t <= 0:
            return np.zeros_like(x)
        return C0 * erfc(x / (2 * np.sqrt(D * t)))

    def simulate_diffusion(
        self,
        ion_type: str,
        thickness_mm: float = 5.0,
        time_hours: float = 1000,
        temperature: float = 25.0,
        humidity: float = 50.0,
        num_points: int = 200,
        surface_normal: Optional[np.ndarray] = None,
        mode: str = 'auto'
    ) -> Dict:
        params = self._PARAMS.get(ion_type)
        if not params:
            raise ValueError(f"未知离子类型: {ion_type}")

        effective_mode = mode
        if mode == 'auto':
            effective_mode = 'anisotropic' if self.use_anisotropic else 'isotropic'

        if effective_mode == 'isotropic':
            return self._simulate_isotropic(
                ion_type, thickness_mm, time_hours, temperature, humidity, num_points, params
            )

        if effective_mode == 'anisotropic' and self.diffusion_tensor is not None:
            return self._simulate_anisotropic(
                ion_type, thickness_mm, time_hours, temperature, humidity,
                num_points, params, surface_normal
            )

        return self._simulate_isotropic(
            ion_type, thickness_mm, time_hours, temperature, humidity, num_points, params
        )

    def _simulate_isotropic(
        self, ion_type, thickness_mm, time_hours, temperature,
        humidity, num_points, params
    ):
        thickness_m = thickness_mm / 1000.0
        x = np.linspace(0, thickness_m, num_points)
        t = time_hours * 3600

        D = self.calculate_diffusion_coefficient(ion_type, temperature, humidity)
        concentration = self.analytical_solution(D, params.surface_concentration, x, t)
        x_mm = x * 1000

        penetration_depth = self.calculate_penetration_depth(concentration, thickness_mm)
        total_amount = np.trapezoid(concentration, x)

        return {
            'ion_type': ion_type,
            'solver_mode': 'isotropic_analytical',
            'diffusion_coefficient': D,
            'anisotropy': self.get_tensor_info(),
            'concentration_profile': concentration.tolist(),
            'depth_profile_mm': x_mm.tolist(),
            'penetration_depth_mm': penetration_depth,
            'total_diffused_amount': float(total_amount),
            'surface_concentration': params.surface_concentration,
            'max_concentration': float(max(concentration)),
            'simulation_time_hours': time_hours,
            'temperature': temperature,
            'humidity': humidity
        }

    def _simulate_anisotropic(
        self, ion_type, thickness_mm, time_hours, temperature,
        humidity, num_points, params, surface_normal
    ):
        thickness_m = thickness_mm / 1000.0
        t = time_hours * 3600

        if surface_normal is None:
            surface_normal = np.array([0, 0, 1])

        D_eff, principal_dir = self.diffusion_tensor.get_surface_normal_diffusivity(
            surface_normal
        )

        T = temperature + 273.15
        D_bulk_ref = params.D0 * np.exp(-params.activation_energy * 1000 / (self.R * T))
        humidity_factor = 0.5 + 0.5 * (humidity / 100.0)
        D_reference = (self.diffusion_tensor.D_parallel +
                       self.diffusion_tensor.D_perp1 +
                       self.diffusion_tensor.D_perp2) / 3.0
        scale_factor = D_bulk_ref * humidity_factor / (D_reference + 1e-25)
        D_scaled = D_eff * scale_factor

        angle_parallel_deg = float(
            np.degrees(np.arccos(
                np.clip(
                    surface_normal @ self.diffusion_tensor.principal_axes[0],
                    -1, 1
                )
            ))
        )

        grain_boundary_enhancement = 1.0 + 0.3 * np.sin(np.radians(angle_parallel_deg)) ** 2
        D_final = D_scaled * grain_boundary_enhancement

        x = np.linspace(0, thickness_m, num_points)
        concentration = self.analytical_solution(
            D_final, params.surface_concentration, x, t
        )
        x_mm = x * 1000

        D_iso = D_bulk_ref * humidity_factor
        anisotropy_correction = (D_final - D_iso) / (D_iso + 1e-25) * 100

        penetration_depth = self.calculate_penetration_depth(concentration, thickness_mm)
        total_amount = np.trapezoid(concentration, x)

        cross_section = None
        try:
            grid_size_3d = (20, 20, num_points)
            spacing = thickness_mm / num_points
            solver = AnisotropicDiffusionSolver(
                self.diffusion_tensor,
                grid_size_mm=grid_size_3d,
                grid_spacing_mm=spacing
            )
            solver.set_boundary_condition(params.surface_concentration, surface_normal)
            dt = min(3600, t / 100)
            solver.step(dt, n_steps=max(1, int(t / dt)))
            cross_section = solver.get_cross_section(0.5, axis=0).tolist()
        except Exception as e:
            warnings.warn(f"3D截面计算失败（{e}），返回1D结果")

        directional_map = self.get_directional_diffusivity_map(
            ion_type, temperature, humidity
        )

        return {
            'ion_type': ion_type,
            'solver_mode': 'anisotropic_tensor',
            'diffusion_coefficient': D_final,
            'diffusion_coefficient_isotropic': D_iso,
            'anisotropy_correction_percent': float(anisotropy_correction),
            'anisotropy': self.get_tensor_info(),
            'crystal_angle_deg': angle_parallel_deg,
            'principal_diffusion_direction': principal_dir.tolist(),
            'grain_boundary_enhancement': float(grain_boundary_enhancement),
            'concentration_profile': concentration.tolist(),
            'depth_profile_mm': x_mm.tolist(),
            'concentration_cross_section_xy': cross_section,
            'directional_diffusivity_map': directional_map,
            'penetration_depth_mm': penetration_depth,
            'penetration_depth_isotropic_mm': self._penetration_isotropic(
                D_iso, params, thickness_mm, t, num_points
            ),
            'total_diffused_amount': float(total_amount),
            'surface_concentration': params.surface_concentration,
            'max_concentration': float(max(concentration)),
            'simulation_time_hours': time_hours,
            'temperature': temperature,
            'humidity': humidity
        }

    def _penetration_isotropic(
        self, D, params, thickness_mm, t, num_points
    ):
        thickness_m = thickness_mm / 1000.0
        x = np.linspace(0, thickness_m, num_points)
        C = self.analytical_solution(D, params.surface_concentration, x, t)
        return self.calculate_penetration_depth(C, thickness_mm)

    def calculate_penetration_depth(
        self,
        concentration: np.ndarray,
        thickness_mm: float,
        threshold_fraction: float = 0.01
    ) -> float:
        if len(concentration) == 0:
            return 0.0

        C_surface = concentration[0]
        if C_surface <= 0:
            return 0.0

        threshold = C_surface * threshold_fraction

        for i in range(len(concentration)):
            if concentration[i] < threshold:
                if i == 0:
                    return 0.0
                ratio = (threshold - concentration[i-1]) / (
                    concentration[i] - concentration[i-1] + 1e-12
                )
                depth = (i - 1 + ratio) * thickness_mm / (len(concentration) - 1)
                return depth

        return thickness_mm

    def simulate_temporal_evolution(
        self,
        ion_type: str,
        thickness_mm: float = 5.0,
        time_points: List[float] = None,
        temperature: float = 25.0,
        humidity: float = 50.0
    ) -> Dict:
        if time_points is None:
            time_points = [1, 10, 100, 500, 1000, 5000]

        profiles = []
        depths = []
        iso_depths = []

        for t in time_points:
            result = self.simulate_diffusion(
                ion_type=ion_type,
                thickness_mm=thickness_mm,
                time_hours=t,
                temperature=temperature,
                humidity=humidity
            )
            profiles.append(result['concentration_profile'])
            depths.append(result['penetration_depth_mm'])
            iso_depths.append(result.get('penetration_depth_isotropic_mm', depths[-1]))

        anisotropy_effect = [
            (d - iso) / (iso + 1e-12) * 100 if iso > 0 else 0
            for d, iso in zip(depths, iso_depths)
        ]

        return {
            'ion_type': ion_type,
            'time_points': time_points,
            'profiles': profiles,
            'penetration_depths': depths,
            'penetration_depths_isotropic': iso_depths,
            'anisotropy_effect_percent': anisotropy_effect,
            'thickness_mm': thickness_mm,
            'tensor_info': self.get_tensor_info()
        }

    def predict_color_intensity(
        self,
        fe_concentration: np.ndarray,
        mn_concentration: np.ndarray
    ) -> np.ndarray:
        fe_weight = 0.6
        mn_weight = 0.4

        base_intensity = fe_weight * fe_concentration + mn_weight * mn_concentration

        if self.use_anisotropic and self.diffusion_tensor is not None:
            n = len(base_intensity)
            crystal_modulation = 1.0 + 0.15 * np.sin(
                np.linspace(0, np.pi * self.diffusion_tensor.anisotropy_ratio, n)
            )
            return base_intensity * crystal_modulation

        return base_intensity

    def temperature_sensitivity_analysis(
        self,
        ion_type: str,
        temp_range: Tuple[float, float],
        thickness_mm: float = 5.0,
        time_hours: float = 1000,
        num_points: int = 20
    ) -> Dict:
        temps = np.linspace(temp_range[0], temp_range[1], num_points)
        depths_aniso = []
        depths_iso = []
        D_values = []

        original_aniso = self.use_anisotropic

        for T in temps:
            self.use_anisotropic = True
            result_a = self.simulate_diffusion(ion_type, thickness_mm, time_hours, T, 50)
            depths_aniso.append(result_a['penetration_depth_mm'])
            depths_iso.append(result_a.get('penetration_depth_isotropic_mm', result_a['penetration_depth_mm']))
            D_values.append(result_a['diffusion_coefficient'])

        self.use_anisotropic = original_aniso

        diffs_pct = [
            (a - i) / (i + 1e-12) * 100 if i > 0 else 0
            for a, i in zip(depths_aniso, depths_iso)
        ]

        return {
            'temperatures': temps.tolist(),
            'diffusion_coefficients': D_values,
            'penetration_depths_anisotropic': depths_aniso,
            'penetration_depths_isotropic': depths_iso,
            'anisotropy_difference_percent': diffs_pct
        }

    def compare_isotropic_vs_anisotropic(
        self,
        ion_type: str,
        thickness_mm: float = 5.0,
        time_hours: float = 5000,
        temperature: float = 25.0
    ) -> Dict:
        original_mode = self.use_anisotropic

        self.use_anisotropic = False
        result_iso = self.simulate_diffusion(
            ion_type, thickness_mm, time_hours, temperature
        )

        self.use_anisotropic = True
        result_aniso = self.simulate_diffusion(
            ion_type, thickness_mm, time_hours, temperature
        )

        self.use_anisotropic = original_mode

        depth_iso = result_iso['penetration_depth_mm']
        depth_aniso = result_aniso['penetration_depth_mm']
        error_pct = abs(depth_aniso - depth_iso) / (depth_iso + 1e-12) * 100

        return {
            'isotropic': {
                'depth_mm': depth_iso,
                'diffusivity': result_iso['diffusion_coefficient'],
                'profile': result_iso['concentration_profile']
            },
            'anisotropic': {
                'depth_mm': depth_aniso,
                'diffusivity': result_aniso['diffusion_coefficient'],
                'profile': result_aniso['concentration_profile'],
                'correction_percent': result_aniso.get('anisotropy_correction_percent', 0),
                'crystal_angle_deg': result_aniso.get('crystal_angle_deg', 0)
            },
            'comparison': {
                'depth_difference_mm': abs(depth_aniso - depth_iso),
                'relative_error_percent': error_pct,
                'tensor_info': result_aniso.get('anisotropy', {}),
                'alert_triggered_iso': depth_iso > 2.0,
                'alert_triggered_aniso': depth_aniso > 2.0,
                'alert_discrepancy': (depth_iso > 2.0) != (depth_aniso > 2.0)
            }
        }
