"""
快速演示脚本 - 不依赖MongoDB也能运行
直接测试核心算法和5G模拟器
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("  古代玉器沁色演化监测与仿古作伪识别系统 - 算法演示")
print("=" * 70)
print()

print("【第一部分】 沁色扩散模型 (菲克第二定律)")
print("-" * 70)

from algorithms.diffusion_model import DiffusionModel

model = DiffusionModel()

print(f"\n1. 扩散系数 (25°C, 50%湿度)")
print(f"   Fe³+ : {model.calculate_diffusion_coefficient('Fe3+', 25, 50):.4e} m²/s")
print(f"   Mn²+ : {model.calculate_diffusion_coefficient('Mn2+', 25, 50):.4e} m²/s")

time_hours = 5000
print(f"\n2. 模拟 {time_hours} 小时 ({time_hours/24/365:.2f} 年) 沁色扩散")

result_fe = model.simulate_diffusion('Fe3+', thickness_mm=5, time_hours=time_hours)
result_mn = model.simulate_diffusion('Mn2+', thickness_mm=5, time_hours=time_hours)

print(f"   Fe³+ 渗透深度: {result_fe['penetration_depth_mm']:.4f} mm  {'⚠️ 超过阈值' if result_fe['penetration_depth_mm'] > 2.0 else '✓ 正常'}")
print(f"   Mn²+ 渗透深度: {result_mn['penetration_depth_mm']:.4f} mm")

max_depth = max(result_fe['penetration_depth_mm'], result_mn['penetration_depth_mm'])
print(f"   最大渗透深度: {max_depth:.4f} mm")
print(f"   告警阈值: 2.0 mm")
if max_depth > 2.0:
    print(f"   >>> 触发沁色深度告警！")

print("\n3. 温度影响 (Fe³+, 5000小时)")
temp_result = model.temperature_sensitivity_analysis('Fe3+', temp_range=(10, 50))
temps = temp_result['temperatures']
depths = temp_result['penetration_depths']
for t, d in [(10, depths[0]), (25, depths[len(depths)//2]), (50, depths[-1])]:
    print(f"   {t:>4.0f}°C: {d:.4f} mm")

print()
print("【第二部分】 孤立森林作伪识别")
print("-" * 70)

from algorithms.isolation_forest import AnomalyDetector

detector = AnomalyDetector(n_estimators=80, contamination=0.15)

print("\n1. 训练模型 (80个正常样本 + 12个异常样本)")
np.random.seed(42)
n_normal = 80
normal_features = np.random.normal(0, 1, (n_normal, 16))
n_anomaly = 12
anomaly_features = np.random.normal(2.5, 1.2, (n_anomaly, 16))
all_features = np.vstack([normal_features, anomaly_features])
detector.train(all_features)
print("   模型训练完成 ✓")

print("\n2. 检测测试")
normal_result = detector.detect(normal_features[0].reshape(1, -1), 'JD0001-真品')
print(f"   真品样本 {normal_result['artifact_id']}:")
print(f"     作伪概率: {normal_result['forgery_probability']*100:.1f}%")
print(f"     风险等级: {normal_result['risk_level']}")

anomaly_result = detector.detect(anomaly_features[0].reshape(1, -1), 'JD0002-疑似伪品')
print(f"   伪品样本 {anomaly_result['artifact_id']}:")
print(f"     作伪概率: {anomaly_result['forgery_probability']*100:.1f}%  {'⚠️ 高风险' if anomaly_result['risk_level'] == 'high' else ''}")
print(f"     风险等级: {anomaly_result['risk_level']}")
print(f"     异常原因: {anomaly_result['anomaly_reasons'][0]}")

print()
print("【第三部分】 5G数据模拟器")
print("-" * 70)

from simulator.jade_simulator import Jade5GSimulator

sim = Jade5GSimulator()

print(f"\n1. 设备配置")
print(f"   拉曼光谱仪: {len(sim.raman_devices)} 台 (RAMAN001 ~ RAMAN020)")
print(f"   X射线荧光仪: {len(sim.xrf_devices)} 台 (XRF001 ~ XRF020)")
print(f"   监测玉器: {sim.artifact_count} 件 (红山文化+良渚文化)")

print(f"\n2. 生成单件玉器光谱数据 (JD0100)")
data = sim.generate_single('JD0100')
print(f"   采集设备: {data['raman']['device_id']}, {data['xrf']['device_id']}")
print(f"   拉曼光谱: {len(data['raman']['data']['spectrum_data'])} 个数据点")
print(f"   XRF光谱: {len(data['xrf']['data']['spectrum_data'])} 个数据点")

raman_spec = data['raman']['data']['spectrum_data']
xrf_spec = data['xrf']['data']['spectrum_data']
print(f"   拉曼强度范围: {min(raman_spec):.4f} ~ {max(raman_spec):.4f}")
print(f"   XRF强度范围: {min(xrf_spec):.4f} ~ {max(xrf_spec):.4f}")

print(f"\n3. 对模拟数据进行作伪识别")
features = detector.extract_features(
    {'spectrum_data': xrf_spec},
    {'spectrum_data': raman_spec}
)
result = detector.detect(features, 'JD0100')
print(f"   作伪概率: {result['forgery_probability']*100:.1f}%")
print(f"   风险等级: {result['risk_level']}")
print(f"   特征维度: {features.shape[1]} 维")

print()
print("=" * 70)
print("  演示完成！系统核心算法运行正常")
print("=" * 70)
print()
print("启动完整系统请执行:")
print("  1. 安装 MongoDB 并运行初始化: mongodb/init.js")
print("  2. 后端: cd backend && python manage.py runserver 0.0.0.0:8000")
print("  3. 前端: 直接打开 frontend/index.html")
print()
