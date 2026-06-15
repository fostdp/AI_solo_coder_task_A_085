import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple


def erf(x):
    """
    误差函数的数值近似 (Abramowitz and Stegun 7.1.26)
    精度约为 1.5e-7
    """
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
    """补余误差函数"""
    return 1.0 - erf(x)


@dataclass
class DiffusionParams:
    D0: float
    activation_energy: float
    surface_concentration: float
    molar_mass: float


class DiffusionModel:
    """
    基于菲克第二定律的沁色扩散模型
    模拟Fe³+和Mn²+等离子在玉器中的扩散过程
    
    菲克第二定律: ∂C/∂t = D * ∂²C/∂x²
    其中 D = D0 * exp(-Q/RT)
    """
    
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
    
    def __init__(self):
        pass
    
    def calculate_diffusion_coefficient(self, ion_type: str, temperature_c: float, 
                                        humidity: float = 50.0) -> float:
        """
        根据阿伦尼乌斯方程计算扩散系数
        D = D0 * exp(-Q/RT) * humidity_factor
        """
        params = self._PARAMS.get(ion_type)
        if not params:
            raise ValueError(f"未知离子类型: {ion_type}")
        
        T = temperature_c + 273.15
        D = params.D0 * np.exp(-params.activation_energy * 1000 / (self.R * T))
        
        humidity_factor = 0.5 + 0.5 * (humidity / 100.0)
        D *= humidity_factor
        
        return D
    
    def analytical_solution(self, D: float, C0: float, x: np.ndarray, t: float) -> np.ndarray:
        """
        菲克第二定律的解析解（半无限介质，恒定表面浓度）
        C(x,t) = C0 * erfc(x/(2*sqrt(D*t)))
        """
        if t <= 0:
            return np.zeros_like(x)
        return C0 * erfc(x / (2 * np.sqrt(D * t)))
    
    def simulate_diffusion(self, ion_type: str, thickness_mm: float = 5.0,
                           time_hours: float = 1000, temperature: float = 25.0,
                           humidity: float = 50.0, num_points: int = 200) -> Dict:
        """
        模拟离子在玉器中的扩散过程
        
        Args:
            ion_type: 离子类型 ('Fe3+', 'Mn2+', 'Cu2+')
            thickness_mm: 玉器厚度 (mm)
            time_hours: 扩散时间 (小时)
            temperature: 环境温度 (°C)
            humidity: 环境湿度 (%)
            num_points: 空间离散点数
        
        Returns:
            包含浓度分布、扩散深度等信息的字典
        """
        params = self._PARAMS.get(ion_type)
        if not params:
            raise ValueError(f"未知离子类型: {ion_type}")
        
        thickness_m = thickness_mm / 1000.0
        x = np.linspace(0, thickness_m, num_points)
        t = time_hours * 3600
        
        D = self.calculate_diffusion_coefficient(ion_type, temperature, humidity)
        
        concentration = self.analytical_solution(D, params.surface_concentration, x, t)
        
        x_mm = x * 1000
        
        penetration_depth = self.calculate_penetration_depth(concentration, thickness_mm)
        
        total_amount = np.trapezoid(concentration, x)
        
        concentration_profile = concentration.tolist()
        
        return {
            'ion_type': ion_type,
            'diffusion_coefficient': D,
            'concentration_profile': concentration_profile,
            'depth_profile_mm': x_mm.tolist(),
            'penetration_depth_mm': penetration_depth,
            'total_diffused_amount': float(total_amount),
            'surface_concentration': params.surface_concentration,
            'max_concentration': float(max(concentration)),
            'simulation_time_hours': time_hours,
            'temperature': temperature,
            'humidity': humidity
        }
    
    def calculate_penetration_depth(self, concentration: np.ndarray, thickness_mm: float) -> float:
        """
        计算有效渗透深度（浓度降至表面浓度1%处的深度）
        """
        if len(concentration) == 0:
            return 0.0
        
        C_surface = concentration[0]
        if C_surface <= 0:
            return 0.0
        
        threshold = C_surface * 0.01
        
        for i in range(len(concentration)):
            if concentration[i] < threshold:
                ratio = (threshold - concentration[i-1]) / (concentration[i] - concentration[i-1] + 1e-10)
                depth = (i - 1 + ratio) * thickness_mm / (len(concentration) - 1)
                return depth
        
        return thickness_mm
    
    def simulate_temporal_evolution(self, ion_type: str, thickness_mm: float = 5.0,
                                    time_points: List[float] = None,
                                    temperature: float = 25.0,
                                    humidity: float = 50.0) -> Dict:
        """
        模拟不同时间点的浓度分布演化
        """
        if time_points is None:
            time_points = [1, 10, 100, 500, 1000, 5000]
        
        profiles = []
        depths = []
        
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
        
        return {
            'ion_type': ion_type,
            'time_points': time_points,
            'profiles': profiles,
            'penetration_depths': depths,
            'thickness_mm': thickness_mm
        }
    
    def predict_color_intensity(self, fe_concentration: np.ndarray, 
                                mn_concentration: np.ndarray) -> np.ndarray:
        """
        根据Fe³+和Mn²+浓度预测沁色强度
        颜色强度与离子浓度的加权和成比例
        """
        fe_weight = 0.6
        mn_weight = 0.4
        return fe_weight * fe_concentration + mn_weight * mn_concentration
    
    def temperature_sensitivity_analysis(self, ion_type: str, temp_range: Tuple[float, float],
                                         thickness_mm: float = 5.0,
                                         time_hours: float = 1000,
                                         num_points: int = 20) -> Dict:
        """
        温度敏感性分析
        """
        temps = np.linspace(temp_range[0], temp_range[1], num_points)
        depths = []
        D_values = []
        
        for T in temps:
            D = self.calculate_diffusion_coefficient(ion_type, T, 50)
            result = self.simulate_diffusion(ion_type, thickness_mm, time_hours, T, 50)
            depths.append(result['penetration_depth_mm'])
            D_values.append(D)
        
        return {
            'temperatures': temps.tolist(),
            'diffusion_coefficients': D_values,
            'penetration_depths': depths
        }
