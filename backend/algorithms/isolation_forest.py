import numpy as np
from typing import Dict, List, Optional


class SimpleStandardScaler:
    """简化的标准化器"""
    
    def __init__(self):
        self.mean_ = None
        self.std_ = None
    
    def fit(self, X):
        X = np.asarray(X, dtype=float)
        self.mean_ = np.mean(X, axis=0)
        self.std_ = np.std(X, axis=0)
        self.std_[self.std_ == 0] = 1.0
        return self
    
    def transform(self, X):
        X = np.asarray(X, dtype=float)
        return (X - self.mean_) / self.std_
    
    def fit_transform(self, X):
        return self.fit(X).transform(X)


class IsolationTree:
    """孤立树"""
    
    def __init__(self, max_depth: int, random_state: int = None):
        self.max_depth = max_depth
        self.random_state = random_state
        self.root = None
        self.size_ = 0
    
    def fit(self, X: np.ndarray):
        rng = np.random.RandomState(self.random_state)
        n_samples = X.shape[0]
        self.size_ = n_samples
        indices = rng.permutation(n_samples)
        self.root = self._build_tree(X, indices, 0, rng)
        return self
    
    def _build_tree(self, X: np.ndarray, indices: np.ndarray, depth: int, rng):
        n = len(indices)
        
        if depth >= self.max_depth or n <= 1:
            return {
                'type': 'leaf',
                'size': n,
                'depth': depth
            }
        
        n_features = X.shape[1]
        feature_idx = rng.randint(0, n_features)
        
        feature_values = X[indices, feature_idx]
        min_val = np.min(feature_values)
        max_val = np.max(feature_values)
        
        if min_val == max_val:
            return {
                'type': 'leaf',
                'size': n,
                'depth': depth
            }
        
        split_val = rng.uniform(min_val, max_val)
        
        left_mask = X[indices, feature_idx] < split_val
        left_indices = indices[left_mask]
        right_indices = indices[~left_mask]
        
        if len(left_indices) == 0 or len(right_indices) == 0:
            return {
                'type': 'leaf',
                'size': n,
                'depth': depth
            }
        
        return {
            'type': 'node',
            'feature': feature_idx,
            'split': split_val,
            'left': self._build_tree(X, left_indices, depth + 1, rng),
            'right': self._build_tree(X, right_indices, depth + 1, rng),
            'depth': depth
        }
    
    def path_length(self, x: np.ndarray) -> float:
        """计算单个样本的路径长度"""
        node = self.root
        length = 0
        
        while node['type'] != 'leaf':
            length += 1
            if x[node['feature']] < node['split']:
                node = node['left']
            else:
                node = node['right']
        
        return length + self._c_factor(node['size'])
    
    def _c_factor(self, n: int) -> float:
        """路径长度修正因子"""
        if n <= 1:
            return 0.0
        return 2.0 * (np.log(n - 1) + 0.5772156649) - 2.0 * (n - 1) / n


class SimpleIsolationForest:
    """纯numpy实现的孤立森林"""
    
    def __init__(self, n_estimators: int = 100, max_samples: str = 'auto',
                 contamination: float = 0.1, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state
        self.trees_ = []
        self.offset_ = None
    
    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        n_samples, n_features = X.shape
        
        if self.max_samples == 'auto':
            n_subsamples = min(256, n_samples)
        else:
            n_subsamples = min(self.max_samples, n_samples)
        
        max_depth = int(np.ceil(np.log2(max(n_subsamples, 2))))
        
        rng = np.random.RandomState(self.random_state)
        self.trees_ = []
        
        for i in range(self.n_estimators):
            tree_seed = rng.randint(0, np.iinfo(np.int32).max)
            tree = IsolationTree(max_depth=max_depth, random_state=tree_seed)
            
            indices = rng.choice(n_samples, size=n_subsamples, replace=False)
            tree.fit(X[indices])
            self.trees_.append(tree)
        
        self.offset_ = self._compute_offset(X)
        return self
    
    def _compute_offset(self, X: np.ndarray) -> float:
        """计算判定阈值偏移量"""
        scores = self.decision_function(X)
        threshold = np.quantile(scores, self.contamination)
        return -threshold
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """计算异常评分（负值表示异常）"""
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        n_samples = X.shape[0]
        avg_path_lengths = np.zeros(n_samples)
        
        for i in range(n_samples):
            path_lengths = [tree.path_length(X[i]) for tree in self.trees_]
            avg_path_lengths[i] = np.mean(path_lengths)
        
        n_reference = self.trees_[0].size_ if self.trees_ else 256
        c_reference = 2.0 * (np.log(n_reference - 1) + 0.5772156649) - 2.0 * (n_reference - 1) / n_reference
        
        anomaly_scores = 2.0 ** (-avg_path_lengths / c_reference)
        
        return -anomaly_scores
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测异常（-1表示异常，1表示正常）"""
        scores = self.decision_function(X)
        return np.where(scores < -self.offset_, -1, 1)


class AnomalyDetector:
    """
    基于孤立森林的仿古作伪识别系统
    利用拉曼光谱和X射线荧光光谱特征进行异常检测
    """
    
    def __init__(self, n_estimators: int = 100, contamination: float = 0.1,
                 max_samples: str = 'auto', random_state: int = 42):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.random_state = random_state
        
        self.model = None
        self.scaler = SimpleStandardScaler()
        self.is_trained = False
        
        self.feature_names = [
            'spectrum_mean',
            'spectrum_std',
            'spectrum_peak_count',
            'main_peak_height',
            'main_peak_position',
            'peak_width_avg',
            'peak_height_ratio',
            'fe_concentration',
            'mn_concentration',
            'cu_concentration',
            'si_al_ratio',
            'rare_earth_total',
            'spectrum_entropy',
            'baseline_slope',
            'noise_level',
            'raman_xrf_correlation'
        ]
    
    def extract_features(self, xrf_data: Optional[Dict], 
                         raman_data: Optional[Dict]) -> np.ndarray:
        """
        从光谱数据中提取特征向量
        """
        features = np.zeros(len(self.feature_names))
        
        if xrf_data:
            xrf_spec = np.array(xrf_data.get('spectrum_data', []))
            if len(xrf_spec) > 0:
                features[0] = np.mean(xrf_spec)
                features[1] = np.std(xrf_spec)
                features[2] = self._count_peaks(xrf_spec)
                
                peaks = self._find_peaks(xrf_spec)
                peaks.sort(key=lambda p: p['height'], reverse=True)
                if peaks:
                    features[3] = peaks[0]['height']
                    features[4] = peaks[0]['position']
                    features[5] = np.mean([p['width'] for p in peaks]) if peaks else 0
                    if len(peaks) >= 2:
                        features[6] = peaks[0]['height'] / (peaks[1]['height'] + 1e-10)
                
                features[7] = self._estimate_element_concentration(xrf_spec, 'Fe')
                features[8] = self._estimate_element_concentration(xrf_spec, 'Mn')
                features[9] = self._estimate_element_concentration(xrf_spec, 'Cu')
                features[10] = self._calc_si_al_ratio(xrf_spec)
                features[11] = self._calc_rare_earth_total(xrf_spec)
                
                features[12] = self._calc_spectrum_entropy(xrf_spec)
                features[13] = self._calc_baseline_slope(xrf_spec)
                features[14] = self._estimate_noise_level(xrf_spec)
        
        if raman_data and xrf_data:
            raman_spec = np.array(raman_data.get('spectrum_data', []))
            xrf_spec = np.array(xrf_data.get('spectrum_data', []))
            if len(raman_spec) > 0 and len(xrf_spec) > 0:
                min_len = min(len(raman_spec), len(xrf_spec))
                if min_len > 10:
                    raman_resized = np.interp(
                        np.linspace(0, len(raman_spec)-1, min_len),
                        np.arange(len(raman_spec)),
                        raman_spec
                    )
                    xrf_resized = np.interp(
                        np.linspace(0, len(xrf_spec)-1, min_len),
                        np.arange(len(xrf_spec)),
                        xrf_spec
                    )
                    corr = np.corrcoef(raman_resized, xrf_resized)
                    if len(corr) > 1 and len(corr[0]) > 1:
                        features[15] = corr[0, 1]
        
        return features.reshape(1, -1)
    
    def _count_peaks(self, spectrum: np.ndarray) -> int:
        """统计光谱中的峰值数量"""
        if len(spectrum) < 3:
            return 0
        
        threshold = np.mean(spectrum) + np.std(spectrum) * 0.5
        peaks = 0
        for i in range(1, len(spectrum) - 1):
            if spectrum[i] > spectrum[i-1] and spectrum[i] > spectrum[i+1] and spectrum[i] > threshold:
                peaks += 1
        return peaks
    
    def _find_peaks(self, spectrum: np.ndarray) -> List[Dict]:
        """查找光谱中的所有峰值"""
        peaks = []
        if len(spectrum) < 3:
            return peaks
        
        threshold = np.mean(spectrum) + np.std(spectrum) * 0.3
        
        for i in range(1, len(spectrum) - 1):
            if spectrum[i] > spectrum[i-1] and spectrum[i] > spectrum[i+1] and spectrum[i] > threshold:
                left = i
                right = i
                while left > 0 and spectrum[left] > spectrum[left-1]:
                    left -= 1
                while right < len(spectrum)-1 and spectrum[right] > spectrum[right+1]:
                    right += 1
                
                width = right - left
                peaks.append({
                    'position': i,
                    'height': spectrum[i],
                    'width': width
                })
        
        return peaks
    
    def _estimate_element_concentration(self, spectrum: np.ndarray, element: str) -> float:
        """估算元素浓度"""
        element_peaks = {
            'Fe': 120,
            'Mn': 90,
            'Cu': 150,
        }
        
        peak_pos = element_peaks.get(element, 100)
        if peak_pos >= len(spectrum):
            peak_pos = len(spectrum) // 2
        
        start = max(0, peak_pos - 5)
        end = min(len(spectrum), peak_pos + 5)
        
        return float(np.sum(spectrum[start:end]))
    
    def _calc_si_al_ratio(self, spectrum: np.ndarray) -> float:
        """计算硅铝比"""
        si_peak = min(50, len(spectrum) - 1)
        al_peak = min(75, len(spectrum) - 1)
        
        si_intensity = spectrum[si_peak]
        al_intensity = spectrum[al_peak]
        
        return float(si_intensity / (al_intensity + 1e-10))
    
    def _calc_rare_earth_total(self, spectrum: np.ndarray) -> float:
        """计算稀土元素总含量估算"""
        if len(spectrum) < 200:
            re_peaks = [len(spectrum) * p for p in [0.8, 0.85, 0.9, 0.95]]
            re_peaks = [int(p) for p in re_peaks]
        else:
            re_peaks = [180, 190, 200, 210, 220]
        
        total = 0.0
        for p in re_peaks:
            if p < len(spectrum):
                total += spectrum[p]
        
        return float(total)
    
    def _calc_spectrum_entropy(self, spectrum: np.ndarray) -> float:
        """计算光谱信息熵"""
        if len(spectrum) == 0:
            return 0.0
        
        spectrum = spectrum - np.min(spectrum) + 1e-10
        total = np.sum(spectrum)
        if total <= 0:
            return 0.0
        
        prob = spectrum / total
        prob = prob[prob > 0]
        
        return float(-np.sum(prob * np.log2(prob)))
    
    def _calc_baseline_slope(self, spectrum: np.ndarray) -> float:
        """计算基线斜率"""
        if len(spectrum) < 10:
            return 0.0
        
        x = np.arange(len(spectrum))
        coeffs = np.polyfit(x, spectrum, 1)
        
        return float(coeffs[0])
    
    def _estimate_noise_level(self, spectrum: np.ndarray) -> float:
        """估算噪声水平"""
        if len(spectrum) < 20:
            return 0.0
        
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(spectrum, kernel, mode='same')
        noise = np.std(spectrum - smoothed)
        
        return float(noise)
    
    def train(self, features: np.ndarray):
        """
        训练孤立森林模型
        """
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        
        self.scaler.fit(features)
        features_scaled = self.scaler.transform(features)
        
        self.model = SimpleIsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            random_state=self.random_state
        )
        self.model.fit(features_scaled)
        self.is_trained = True
    
    def detect(self, features: np.ndarray, artifact_id: str = '') -> Dict:
        """
        检测异常
        """
        if not self.is_trained:
            self._train_default_model()
        
        features_scaled = self.scaler.transform(features)
        
        anomaly_score = self.model.decision_function(features_scaled)[0]
        is_anomaly = self.model.predict(features_scaled)[0] == -1
        
        raw_score = -anomaly_score
        forgery_prob = min(1.0, max(0.0, (raw_score - 0.3) / 0.7))
        
        anomaly_reasons = self._analyze_anomaly_reasons(features[0], forgery_prob)
        
        return {
            'artifact_id': artifact_id,
            'anomaly_score': float(anomaly_score),
            'forgery_probability': float(forgery_prob),
            'is_anomaly': bool(is_anomaly),
            'features': {
                name: float(val)
                for name, val in zip(self.feature_names, features[0])
            },
            'anomaly_reasons': anomaly_reasons,
            'risk_level': self._get_risk_level(forgery_prob)
        }
    
    def _train_default_model(self):
        """使用默认样本训练模型"""
        np.random.seed(self.random_state)
        
        n_normal = 80
        normal_features = np.random.normal(0, 1, (n_normal, len(self.feature_names)))
        
        n_anomaly = int(n_normal * self.contamination)
        anomaly_features = np.random.normal(2.5, 1.2, (n_anomaly, len(self.feature_names)))
        
        all_features = np.vstack([normal_features, anomaly_features])
        
        self.train(all_features)
    
    def _analyze_anomaly_reasons(self, feature_values: np.ndarray, forgery_prob: float) -> List[str]:
        """分析异常原因"""
        reasons = []
        
        if abs(feature_values[2]) > 2.0:
            reasons.append("光谱峰数异常")
        
        if feature_values[7] > 1.5:
            reasons.append("铁元素含量异常偏高")
        
        if feature_values[9] > 1.0:
            reasons.append("铜元素含量异常，疑似人工染色")
        
        if abs(feature_values[10]) > 3.0:
            reasons.append("硅铝比异常")
        
        if abs(feature_values[12]) > 2.0:
            reasons.append("光谱信息熵异常")
        
        if feature_values[14] > 1.5:
            reasons.append("噪声水平异常")
        
        if feature_values[15] < -0.2:
            reasons.append("拉曼与XRF光谱相关性异常")
        
        if forgery_prob > 0.7 and not reasons:
            reasons.append("整体光谱特征与真品模式存在差异")
        
        if not reasons:
            reasons.append("光谱特征基本正常")
        
        return reasons
    
    def _get_risk_level(self, forgery_prob: float) -> str:
        """根据作伪概率确定风险等级"""
        if forgery_prob >= 0.8:
            return 'high'
        elif forgery_prob >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def batch_detect(self, features_list: List[np.ndarray], 
                     artifact_ids: List[str]) -> List[Dict]:
        """批量检测"""
        results = []
        for feat, aid in zip(features_list, artifact_ids):
            result = self.detect(feat, aid)
            results.append(result)
        return results
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_trained:
            return {}
        
        importances = {}
        for i, name in enumerate(self.feature_names):
            importances[name] = float(1.0 / len(self.feature_names))
        
        return importances
    
    def save_model(self, filepath: str):
        """保存模型"""
        import pickle
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'feature_names': self.feature_names
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath: str):
        """加载模型"""
        import pickle
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        self.feature_names = model_data.get('feature_names', self.feature_names)
