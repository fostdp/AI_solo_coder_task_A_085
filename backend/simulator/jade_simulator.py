import threading
import time
import random
import numpy as np
from datetime import datetime
import logging
import requests

logger = logging.getLogger(__name__)


class Jade5GSimulator:
    """
    5G数据模拟器
    模拟拉曼光谱仪和X射线荧光光谱仪每6小时上报数据
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.is_running = False
        self.thread = None
        self.interval = 30
        self.artifact_count = 200
        self.raman_devices = [f"RAMAN{str(i).zfill(3)}" for i in range(1, 21)]
        self.xrf_devices = [f"XRF{str(i).zfill(3)}" for i in range(1, 21)]
        
        self.base_spectra_cache = {}
    
    def start(self, interval: int = 30):
        """
        启动模拟器
        
        Args:
            interval: 上报间隔（秒），默认30秒模拟6小时
        """
        if self.is_running:
            logger.warning("模拟器已在运行")
            return
        
        self.interval = interval
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"5G数据模拟器已启动，上报间隔: {interval}秒")
    
    def stop(self):
        """停止模拟器"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("5G数据模拟器已停止")
    
    def _run(self):
        """模拟器主循环"""
        while self.is_running:
            try:
                self._generate_batch_data()
            except Exception as e:
                logger.error(f"模拟器运行出错: {e}")
            
            time.sleep(self.interval)
    
    def _generate_batch_data(self):
        """生成一批数据（模拟所有设备的一次上报）"""
        logger.info(f"开始生成光谱数据，时间: {datetime.now()}")
        
        artifact_ids = [f"JD{str(i).zfill(4)}" for i in range(1, self.artifact_count + 1)]
        
        for i, artifact_id in enumerate(artifact_ids):
            try:
                raman_device = self.raman_devices[i % len(self.raman_devices)]
                xrf_device = self.xrf_devices[i % len(self.xrf_devices)]
                
                raman_data = self._generate_raman_spectrum(artifact_id)
                xrf_data = self._generate_xrf_spectrum(artifact_id)
                
                self._upload_spectrum(artifact_id, raman_device, 'raman', raman_data)
                self._upload_spectrum(artifact_id, xrf_device, 'xrf', xrf_data)
                
            except Exception as e:
                logger.error(f"生成玉器 {artifact_id} 数据失败: {e}")
        
        logger.info(f"完成 {self.artifact_count} 件玉器的光谱数据生成")
    
    def _generate_raman_spectrum(self, artifact_id: str) -> dict:
        """
        生成拉曼光谱数据
        
        拉曼光谱典型特征:
        - 硅氧键振动: ~500 cm⁻¹
        - 金属氧键: 100-300 cm⁻¹
        - 碳酸盐: ~1080 cm⁻¹
        """
        num_points = 512
        wavelengths = np.linspace(100, 2000, num_points)
        
        if artifact_id not in self.base_spectra_cache:
            base_intensity = np.zeros(num_points)
            
            self._add_peak(base_intensity, wavelengths, 200, 1.0, 30)
            self._add_peak(base_intensity, wavelengths, 380, 0.8, 40)
            self._add_peak(base_intensity, wavelengths, 520, 1.5, 50)
            self._add_peak(base_intensity, wavelengths, 700, 0.6, 35)
            self._add_peak(base_intensity, wavelengths, 1080, 0.9, 45)
            
            base_intensity += np.random.normal(0, 0.02, num_points)
            self.base_spectra_cache[artifact_id] = base_intensity.copy()
        
        intensity = self.base_spectra_cache[artifact_id].copy()
        
        drift = np.random.normal(0, 0.01, num_points)
        intensity += drift
        
        noise_level = 0.03
        noise = np.random.normal(0, noise_level, num_points)
        intensity += noise
        
        intensity = np.maximum(intensity, 0)
        
        return {
            'wavelengths': wavelengths.tolist(),
            'spectrum_data': intensity.tolist(),
            'laser_wavelength': 532,
            'exposure_time': 10,
            'accumulations': 3
        }
    
    def _generate_xrf_spectrum(self, artifact_id: str) -> dict:
        """
        生成X射线荧光光谱数据
        
        主要元素特征峰:
        - Si Kα: 1.74 keV
        - O Kα: 0.525 keV
        - Fe Kα: 6.40 keV
        - Ca Kα: 3.69 keV
        - Al Kα: 1.49 keV
        - Mn Kα: 5.90 keV
        - Cu Kα: 8.04 keV
        """
        num_points = 256
        energies = np.linspace(0, 15, num_points)
        
        if artifact_id not in self.base_spectra_cache:
            self.base_spectra_cache[artifact_id] = {}
        
        cache_key = 'xrf_' + artifact_id
        if cache_key not in self.base_spectra_cache:
            base_intensity = np.zeros(num_points)
            
            self._add_peak(base_intensity, energies, 0.525, 1.2, 0.05)
            self._add_peak(base_intensity, energies, 1.49, 0.8, 0.04)
            self._add_peak(base_intensity, energies, 1.74, 1.5, 0.06)
            self._add_peak(base_intensity, energies, 3.69, 0.6, 0.05)
            self._add_peak(base_intensity, energies, 6.40, 0.4, 0.04)
            self._add_peak(base_intensity, energies, 5.90, 0.15, 0.03)
            self._add_peak(base_intensity, energies, 8.04, 0.1, 0.02)
            
            background = 0.05 * np.exp(-energies / 2)
            base_intensity += background
            
            base_intensity += np.random.normal(0, 0.005, num_points)
            self.base_spectra_cache[cache_key] = base_intensity.copy()
        
        intensity = self.base_spectra_cache[cache_key].copy()
        
        drift_factor = 1 + np.random.normal(0, 0.02)
        intensity *= drift_factor
        
        noise = np.random.normal(0, 0.01, num_points)
        intensity += noise
        intensity = np.maximum(intensity, 0)
        
        is_suspect = hash(artifact_id) % 100 < 15
        if is_suspect:
            fe_peak_idx = np.argmin(np.abs(energies - 6.40))
            intensity[fe_peak_idx-5:fe_peak_idx+5] *= 2.5
            
            cu_peak_idx = np.argmin(np.abs(energies - 8.04))
            intensity[cu_peak_idx-3:cu_peak_idx+3] *= 3.0
        
        return {
            'energies': energies.tolist(),
            'spectrum_data': intensity.tolist(),
            'tube_voltage': 40,
            'tube_current': 100,
            'measurement_time': 30
        }
    
    def _add_peak(self, spectrum: np.ndarray, x_axis: np.ndarray, 
                  center: float, height: float, width: float):
        """向光谱添加高斯峰"""
        peak = height * np.exp(-((x_axis - center) ** 2) / (2 * width ** 2))
        spectrum += peak
    
    def _upload_spectrum(self, artifact_id: str, device_id: str, 
                         spectrum_type: str, spectrum_data: dict):
        """
        上传光谱数据到后端
        
        Args:
            artifact_id: 玉器ID
            device_id: 设备ID
            spectrum_type: 光谱类型 ('raman' 或 'xrf')
            spectrum_data: 光谱数据
        """
        try:
            payload = {
                'artifact_id': artifact_id,
                'device_id': device_id,
                'type': spectrum_type,
                'spectrum_data': spectrum_data['spectrum_data'],
                'wavelengths': spectrum_data.get('wavelengths', []),
                'energies': spectrum_data.get('energies', [])
            }
            
            url = f"{self.base_url}/api/spectrum/upload/"
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"上传成功: {artifact_id} - {spectrum_type}")
            else:
                logger.warning(f"上传失败: {artifact_id} - {spectrum_type} - {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"上传连接失败: {e}")
    
    def generate_single(self, artifact_id: str) -> dict:
        """生成单个玉器的完整数据"""
        raman_device = self.raman_devices[hash(artifact_id) % len(self.raman_devices)]
        xrf_device = self.xrf_devices[hash(artifact_id) % len(self.xrf_devices)]
        
        return {
            'artifact_id': artifact_id,
            'timestamp': datetime.now().isoformat(),
            'raman': {
                'device_id': raman_device,
                'data': self._generate_raman_spectrum(artifact_id)
            },
            'xrf': {
                'device_id': xrf_device,
                'data': self._generate_xrf_spectrum(artifact_id)
            }
        }


simulator = Jade5GSimulator()
