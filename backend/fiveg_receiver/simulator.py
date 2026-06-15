import threading
import time
import random
import numpy as np
from datetime import datetime
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class NetworkQoSConfig:
    bandwidth_mhz: float = 100.0
    peak_throughput_gbps: float = 1.0
    sustained_throughput_gbps: float = 0.8
    latency_ms: float = 10.0
    jitter_ms: float = 2.0
    packet_loss_rate: float = 0.001
    max_queue_packets: int = 1000


@dataclass
class NetworkStats:
    total_bytes_sent: int = 0
    total_packets_sent: int = 0
    total_packets_dropped: int = 0
    avg_latency_ms: float = 0.0
    current_throughput_mbps: float = 0.0
    queue_occupancy: int = 0
    congestion_level: float = 0.0


class TokenBucket:

    def __init__(self, rate_bits_per_sec: float, bucket_size_bits: float):
        self.rate = rate_bits_per_sec
        self.bucket_size = bucket_size_bits
        self.current_tokens = bucket_size_bits
        self.last_update = time.time()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_update
        if elapsed > 0:
            self.current_tokens = min(
                self.bucket_size,
                self.current_tokens + elapsed * self.rate
            )
            self.last_update = now

    def consume(self, bits: float, block: bool = True, timeout: float = 5.0) -> bool:
        start_time = time.time()
        with self._lock:
            while True:
                self._refill()
                if self.current_tokens >= bits:
                    self.current_tokens -= bits
                    return True

                if not block:
                    return False

                wait_time = (bits - self.current_tokens) / self.rate
                wait_time = min(wait_time, timeout - (time.time() - start_time))

                if wait_time <= 0:
                    return False

                time.sleep(wait_time)

                if time.time() - start_time >= timeout:
                    return False

    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self.current_tokens

    def set_rate(self, new_rate_bits_per_sec: float):
        with self._lock:
            self._refill()
            self.rate = new_rate_bits_per_sec


class FiveGNetworkSimulator:

    BAND_CONFIGS = {
        'n78': {'bandwidth': 100, 'peak_gbps': 1.0, 'freq': '3.5GHz'},
        'n41': {'bandwidth': 100, 'peak_gbps': 0.8, 'freq': '2.6GHz'},
        'n77': {'bandwidth': 100, 'peak_gbps': 1.2, 'freq': '3.3GHz'},
        'n257': {'bandwidth': 400, 'peak_gbps': 5.0, 'freq': '28GHz'},
        'n79': {'bandwidth': 100, 'peak_gbps': 0.9, 'freq': '4.9GHz'},
    }

    QOS_FLOWS = {
        'embb': {'priority': 2, 'latency_budget_ms': 100, 'name': '增强移动宽带'},
        'urllc': {'priority': 1, 'latency_budget_ms': 10, 'name': '超可靠低时延'},
        'mmtc': {'priority': 5, 'latency_budget_ms': 1000, 'name': '海量机器类通信'},
    }

    def __init__(self, band: str = 'n78', qos_config: Optional[NetworkQoSConfig] = None):
        self.band = band
        band_cfg = self.BAND_CONFIGS.get(band, self.BAND_CONFIGS['n78'])

        if qos_config is None:
            qos_config = NetworkQoSConfig(
                bandwidth_mhz=band_cfg['bandwidth'],
                peak_throughput_gbps=band_cfg['peak_gbps']
            )

        self.qos_config = qos_config

        peak_bps = qos_config.peak_throughput_gbps * 1e9
        sustained_bps = qos_config.sustained_throughput_gbps * 1e9

        self.token_bucket = TokenBucket(
            rate_bits_per_sec=sustained_bps,
            bucket_size_bits=peak_bps * 0.1
        )

        self._queue: Deque[Dict] = deque()
        self._queue_lock = threading.Lock()

        self.stats = NetworkStats()
        self._history: Deque[tuple] = deque(maxlen=100)
        self._last_throughput_calc = time.time()
        self._bytes_in_window = 0

        self._congestion_control_enabled = True
        self._current_rate_multiplier = 1.0

        self._scheduler_running = False
        self._scheduler_thread: Optional[threading.Thread] = None

    def start(self):
        if self._scheduler_running:
            return
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name='5G-Scheduler'
        )
        self._scheduler_thread.start()
        logger.info(
            f"5G 网络模拟器已启动，频段: {self.band} "
            f"({self.BAND_CONFIGS[self.band]['freq']}), "
            f"带宽: {self.qos_config.bandwidth_mhz}MHz, "
            f"峰值: {self.qos_config.peak_throughput_gbps}Gbps"
        )

    def stop(self):
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2)
        logger.info("5G 网络模拟器已停止")

    def _scheduler_loop(self):
        while self._scheduler_running:
            try:
                self._process_queue()
                self._update_stats()
                self._congestion_control()
                time.sleep(0.001)
            except Exception as e:
                logger.error(f"5G 调度器错误: {e}")
                time.sleep(0.01)

    def _process_queue(self):
        with self._queue_lock:
            if not self._queue:
                self.stats.queue_occupancy = 0
                return

            self.stats.queue_occupancy = len(self._queue)
            packet = self._queue.popleft()

        latency = (
            self.qos_config.latency_ms
            + np.random.normal(0, self.qos_config.jitter_ms)
        )
        latency = max(0.1, latency)

        if random.random() < self.qos_config.packet_loss_rate:
            self.stats.total_packets_dropped += 1
            if packet.get('callback'):
                try:
                    packet['callback'](success=False, reason='packet_loss')
                except:
                    pass
            return

        packet_bits = packet['size_bytes'] * 8
        got_tokens = self.token_bucket.consume(
            packet_bits,
            block=True,
            timeout=5.0
        )

        if not got_tokens:
            self.stats.total_packets_dropped += 1
            if packet.get('callback'):
                try:
                    packet['callback'](success=False, reason='timeout')
                except:
                    pass
            return

        time.sleep(latency / 1000.0)

        self.stats.total_bytes_sent += packet['size_bytes']
        self.stats.total_packets_sent += 1
        self._bytes_in_window += packet['size_bytes']

        self.stats.avg_latency_ms = (
            self.stats.avg_latency_ms * 0.95 + latency * 0.05
        )

        if packet.get('callback'):
            try:
                packet['callback'](
                    success=True,
                    latency_ms=latency,
                    throughput_mbps=(packet_bits / (latency / 1000)) / 1e6
                )
            except:
                pass

    def _update_stats(self):
        now = time.time()
        window = now - self._last_throughput_calc
        if window >= 1.0:
            self.stats.current_throughput_mbps = (
                self._bytes_in_window * 8 / window / 1e6
            )
            self._bytes_in_window = 0
            self._last_throughput_calc = now

            self._history.append((now, self.stats.current_throughput_mbps))

            queue_len = len(self._queue)
            self.stats.congestion_level = min(
                1.0,
                queue_len / self.qos_config.max_queue_packets
            )

    def _congestion_control(self):
        if not self._congestion_control_enabled:
            return

        queue_len = len(self._queue)
        max_queue = self.qos_config.max_queue_packets

        if queue_len > max_queue * 0.5:
            drop_prob = min(
                0.5,
                (queue_len - max_queue * 0.5) / (max_queue * 0.5)
            )
            if random.random() < drop_prob * 0.01:
                with self._queue_lock:
                    if self._queue:
                        self._queue.popleft()
                        self.stats.total_packets_dropped += 1

        target_multiplier = max(0.3, 1.0 - self.stats.congestion_level * 0.7)
        self._current_rate_multiplier = (
            self._current_rate_multiplier * 0.95 + target_multiplier * 0.05
        )

        sustained_bps = (
            self.qos_config.sustained_throughput_gbps
            * 1e9
            * self._current_rate_multiplier
        )
        self.token_bucket.set_rate(sustained_bps)

    def send_packet(
        self,
        data_bytes: int,
        qos_flow: str = 'embb',
        priority: Optional[int] = None,
        callback: Optional[callable] = None
    ) -> bool:
        if len(self._queue) >= self.qos_config.max_queue_packets:
            self.stats.total_packets_dropped += 1
            return False

        if priority is None:
            priority = self.QOS_FLOWS.get(qos_flow, {}).get('priority', 3)

        packet = {
            'size_bytes': data_bytes,
            'qos_flow': qos_flow,
            'priority': priority,
            'timestamp': time.time(),
            'callback': callback
        }

        with self._queue_lock:
            if priority <= 2:
                self._queue.appendleft(packet)
            else:
                self._queue.append(packet)

        return True

    def wait_for_drain(self, timeout: float = 30.0) -> bool:
        start = time.time()
        while len(self._queue) > 0:
            if time.time() - start >= timeout:
                return False
            time.sleep(0.01)
        return True

    def get_stats(self) -> Dict:
        return {
            'band': self.band,
            'bandwidth_mhz': self.qos_config.bandwidth_mhz,
            'peak_throughput_gbps': self.qos_config.peak_throughput_gbps,
            **self.stats.__dict__,
            'queue_size': len(self._queue),
            'rate_multiplier': self._current_rate_multiplier,
            'available_tokens_mb': self.token_bucket.available_tokens() / 8 / 1e6,
        }


class Receiver5GSimulator:

    FORGED_SPECTRA_SIGNATURES = {
        'accelerated_aging': {
            'description': '加速老化仿古',
            'raman_peak_shifts': [(520, 525, 0.8), (380, 385, 0.6)],
            'xrf_enhancements': {'Fe': 3.0, 'Mn': 2.5, 'Cu': 4.0},
            'signature_noise': 0.005,
        },
        'chemical_staining': {
            'description': '化学染色仿古',
            'raman_peak_shifts': [(1080, 1085, 1.2), (700, 710, 0.9)],
            'xrf_enhancements': {'Fe': 2.0, 'Mn': 4.0, 'Pb': 5.0},
            'signature_noise': 0.003,
        },
        'heat_treatment': {
            'description': '高温处理仿古',
            'raman_peak_shifts': [(200, 195, 0.7), (520, 515, 0.5)],
            'xrf_enhancements': {'Fe': 1.5, 'Mn': 1.8, 'Si': 2.2},
            'signature_noise': 0.008,
        },
    }

    FORGERY_INJECTION_API = '/api/simulator/inject_forgery/'

    def __init__(
        self,
        band: str = 'n78',
        enable_network_sim: bool = True,
        device_count: int = 40,
        interval: int = 21600,
    ):
        self.is_running = False
        self.thread = None
        self.interval = interval
        self.artifact_count = 200

        raman_count = device_count // 2
        xrf_count = device_count - raman_count
        self.raman_devices = [f"RAMAN{str(i).zfill(3)}" for i in range(1, raman_count + 1)]
        self.xrf_devices = [f"XRF{str(i).zfill(3)}" for i in range(1, xrf_count + 1)]

        self.base_spectra_cache = {}

        self._forgery_injections: Dict[str, Dict] = {}
        self._forgery_lock = threading.Lock()

        self.enable_network_sim = enable_network_sim
        self.network_sim: Optional[FiveGNetworkSimulator] = None
        if enable_network_sim:
            self.network_sim = FiveGNetworkSimulator(band=band)
            self.network_sim.start()

        self._upload_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'dropped': 0,
            'forgery_injected': 0,
        }

    def start(self, interval: int = None):
        if self.is_running:
            logger.warning("模拟器已在运行")
            return

        if interval is not None:
            self.interval = interval

        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        if self.enable_network_sim and not self.network_sim:
            self.network_sim = FiveGNetworkSimulator()
            self.network_sim.start()

        logger.info(
            "5G接收器模拟器已启动，设备: %d台(拉曼%d+XRF%d)，上报间隔: %d秒(%.1f小时)，"
            "网络模拟: %s",
            len(self.raman_devices) + len(self.xrf_devices),
            len(self.raman_devices), len(self.xrf_devices),
            self.interval, self.interval / 3600.0,
            '启用' if self.enable_network_sim else '禁用'
        )

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.network_sim:
            self.network_sim.stop()
        logger.info(
            "5G接收器模拟器已停止，统计: %s，网络: %s",
            self._upload_stats,
            self.network_sim.get_stats() if self.network_sim else 'N/A'
        )

    def inject_forgery(self, artifact_id: str, forgery_type: str = 'chemical_staining') -> bool:
        if forgery_type not in self.FORGED_SPECTRA_SIGNATURES:
            logger.error("未知仿古类型: %s，可选: %s", forgery_type, list(self.FORGED_SPECTRA_SIGNATURES.keys()))
            return False

        with self._forgery_lock:
            self._forgery_injections[artifact_id] = {
                'type': forgery_type,
                'injected_at': datetime.now().isoformat(),
                **self.FORGED_SPECTRA_SIGNATURES[forgery_type],
            }
            if artifact_id in self.base_spectra_cache:
                del self.base_spectra_cache[artifact_id]
                xrf_key = 'xrf_' + artifact_id
                if xrf_key in self.base_spectra_cache:
                    del self.base_spectra_cache[xrf_key]

        logger.info(
            "已注入仿古光谱: 玉器=%s, 类型=%s(%s)",
            artifact_id, forgery_type,
            self.FORGED_SPECTRA_SIGNATURES[forgery_type]['description']
        )
        return True

    def remove_forgery(self, artifact_id: str) -> bool:
        with self._forgery_lock:
            removed = self._forgery_injections.pop(artifact_id, None)
            if removed:
                if artifact_id in self.base_spectra_cache:
                    del self.base_spectra_cache[artifact_id]
                xrf_key = 'xrf_' + artifact_id
                if xrf_key in self.base_spectra_cache:
                    del self.base_spectra_cache[xrf_key]
                logger.info("已移除仿古注入: %s", artifact_id)
                return True
        return False

    def get_forgery_injections(self) -> Dict:
        with self._forgery_lock:
            return dict(self._forgery_injections)

    def _run(self):
        while self.is_running:
            try:
                self._generate_batch_data()
            except Exception as e:
                logger.error(f"模拟器运行出错: {e}")

            time.sleep(self.interval)

    def _generate_batch_data(self):
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

        if self.network_sim:
            drained = self.network_sim.wait_for_drain(timeout=30)
            if not drained:
                logger.warning("网络队列未在超时时间内排空")

        logger.info(
            f"完成 {self.artifact_count} 件玉器的光谱数据生成，"
            f"统计: {self._upload_stats}, "
            f"网络拥塞: {self.network_sim.stats.congestion_level:.1%}"
            if self.network_sim else ""
        )

    def _estimate_packet_size(self, spectrum_data: dict) -> int:
        import json
        try:
            payload = {
                'artifact_id': 'test',
                'device_id': 'test',
                'type': 'test',
                'spectrum_data': spectrum_data.get('spectrum_data', []),
                'wavelengths': spectrum_data.get('wavelengths', []),
                'energies': spectrum_data.get('energies', [])
            }
            return len(json.dumps(payload).encode('utf-8'))
        except:
            return 8192

    def _upload_spectrum(self, artifact_id: str, device_id: str,
                         spectrum_type: str, spectrum_data: dict):
        self._upload_stats['total'] += 1

        try:
            if self.network_sim:
                packet_size = self._estimate_packet_size(spectrum_data)

                upload_completed = threading.Event()
                upload_result = {'success': False}

                def _network_callback(success, **kwargs):
                    upload_result['success'] = success
                    upload_result.update(kwargs)
                    upload_completed.set()

                queued = self.network_sim.send_packet(
                    data_bytes=packet_size,
                    qos_flow='embb',
                    callback=_network_callback
                )

                if not queued:
                    self._upload_stats['dropped'] += 1
                    logger.debug(
                        f"网络队列已满，丢包: {artifact_id} - {spectrum_type}"
                    )
                    return

                if not upload_completed.wait(timeout=30):
                    self._upload_stats['failed'] += 1
                    logger.debug(
                        f"网络传输超时: {artifact_id} - {spectrum_type}"
                    )
                    return

                if not upload_result['success']:
                    self._upload_stats['failed'] += 1
                    logger.debug(
                        f"网络传输失败: {artifact_id} - {spectrum_type}, "
                        f"原因: {upload_result.get('reason', 'unknown')}"
                    )
                    return

            from .tasks import receive_spectrum
            receive_spectrum.delay(
                artifact_id=artifact_id,
                device_id=device_id,
                spectrum_type=spectrum_type,
                spectrum_data=spectrum_data['spectrum_data'],
                wavelengths=spectrum_data.get('wavelengths', []),
                energies=spectrum_data.get('energies', [])
            )

            self._upload_stats['success'] += 1
            logger.debug(f"已提交Celery任务: {artifact_id} - {spectrum_type}")

        except Exception as e:
            self._upload_stats['failed'] += 1
            logger.debug(f"提交任务失败: {e}")

    def _generate_raman_spectrum(self, artifact_id: str) -> dict:
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

        with self._forgery_lock:
            forgery = self._forgery_injections.get(artifact_id)

        if forgery:
            for orig_center, forged_center, height_mult in forgery.get('raman_peak_shifts', []):
                orig_idx = np.argmin(np.abs(wavelengths - orig_center))
                forged_idx = np.argmin(np.abs(wavelengths - forged_center))
                if orig_idx < num_points and forged_idx < num_points:
                    peak_val = intensity[orig_idx] * height_mult
                    self._add_peak(intensity, wavelengths, forged_center, peak_val, 25)
            noise_level = forgery.get('signature_noise', 0.005)
            intensity += np.random.normal(0, noise_level, num_points)
            self._upload_stats['forgery_injected'] += 1
        else:
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

        with self._forgery_lock:
            forgery = self._forgery_injections.get(artifact_id)

        if forgery:
            xrf_enhancements = forgery.get('xrf_enhancements', {})
            element_peak_map = {
                'Fe': 6.40, 'Mn': 5.90, 'Cu': 8.04,
                'Pb': 10.55, 'Si': 1.74, 'Ca': 3.69,
            }
            for element, multiplier in xrf_enhancements.items():
                peak_energy = element_peak_map.get(element)
                if peak_energy is not None:
                    peak_idx = np.argmin(np.abs(energies - peak_energy))
                    half_w = max(3, int(0.06 / (energies[1] - energies[0])))
                    lo = max(0, peak_idx - half_w)
                    hi = min(num_points, peak_idx + half_w + 1)
                    intensity[lo:hi] *= multiplier
            noise_level = forgery.get('signature_noise', 0.003)
            intensity += np.random.normal(0, noise_level, num_points)
        else:
            drift_factor = 1 + np.random.normal(0, 0.02)
            intensity *= drift_factor
            noise = np.random.normal(0, 0.01, num_points)
            intensity += noise

            is_suspect = hash(artifact_id) % 100 < 15
            if is_suspect:
                fe_peak_idx = np.argmin(np.abs(energies - 6.40))
                intensity[fe_peak_idx-5:fe_peak_idx+5] *= 2.5
                cu_peak_idx = np.argmin(np.abs(energies - 8.04))
                intensity[cu_peak_idx-3:cu_peak_idx+3] *= 3.0

        intensity = np.maximum(intensity, 0)

        return {
            'energies': energies.tolist(),
            'spectrum_data': intensity.tolist(),
            'tube_voltage': 40,
            'tube_current': 100,
            'measurement_time': 30
        }

    def _add_peak(self, spectrum: np.ndarray, x_axis: np.ndarray,
                  center: float, height: float, width: float):
        peak = height * np.exp(-((x_axis - center) ** 2) / (2 * width ** 2))
        spectrum += peak

    def get_network_stats(self) -> Optional[Dict]:
        if self.network_sim:
            return self.network_sim.get_stats()
        return None

    def get_upload_stats(self) -> Dict:
        stats = dict(self._upload_stats)
        if self._upload_stats['total'] > 0:
            stats['success_rate'] = (
                self._upload_stats['success'] / self._upload_stats['total']
            )
        return stats

    def generate_single(self, artifact_id: str) -> dict:
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


def _create_simulator():
    try:
        from django.conf import settings
        device_count = getattr(settings, 'SIMULATOR_DEVICE_COUNT', 40)
        interval = getattr(settings, 'SIMULATOR_INTERVAL', 21600)
        band = getattr(settings, 'FIVE_G_BAND', 'n78')
    except Exception:
        device_count = 40
        interval = 21600
        band = 'n78'
    return Receiver5GSimulator(band=band, device_count=device_count, interval=interval)

simulator = _create_simulator()
