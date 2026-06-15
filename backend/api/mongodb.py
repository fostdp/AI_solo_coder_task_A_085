from pymongo import MongoClient
from django.conf import settings

_era_map = {
    '红山文化': 'neolithic_hongshan',
    '良渚文化': 'neolithic_liangzhu',
    '龙山文化': 'neolithic_longshan',
    '商代': 'shang',
    '西周': 'western_zhou',
    '春秋': 'spring_autumn',
    '战国': 'warring_states',
    '汉代': 'han',
}


def get_era_key(culture: str) -> str:
    return _era_map.get(culture, 'other')


def get_db():
    client = MongoClient(
        settings.MONGODB_DATABASES['default']['host'],
        settings.MONGODB_DATABASES['default']['port']
    )
    return client[settings.MONGODB_DATABASES['default']['name']]


def get_collection(collection_name):
    db = get_db()
    return db[collection_name]


def ensure_shard_indexes():
    try:
        db = get_db()
        for coll_name in ['jade_artifacts', 'raman_spectrum', 'xrf_spectrum',
                          'diffusion_results', 'anomaly_results', 'alerts']:
            db[coll_name].create_index('era')
    except Exception:
        pass
