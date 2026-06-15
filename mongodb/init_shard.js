// MongoDB Sharding Initialization Script
// Shard key: era (玉器年代), distributes data by archaeological era

// Enable sharding on the jade_monitor database
sh.enableSharding("jade_monitor");

// Shard collections by era field
// Each era (红山文化, 良渚文化, etc.) maps to a shard partition
// This enables efficient queries like "find all 红山文化 artifacts"

sh.shardCollection("jade_monitor.jade_artifacts", {"era": 1});
sh.shardCollection("jade_monitor.raman_spectrum", {"era": 1});
sh.shardCollection("jade_monitor.xrf_spectrum", {"era": 1});
sh.shardCollection("jade_monitor.diffusion_results", {"era": 1});
sh.shardCollection("jade_monitor.anomaly_results", {"era": 1});
sh.shardCollection("jade_monitor.alerts", {"era": 1});

// Tag-aware sharding: assign shards to era ranges
// shard01 -> neolithic (红山, 良渚)
// shard02 -> later eras (商, 周, 汉)
sh.addShardTag("shardRs01", "neolithic");
sh.addShardTag("shardRs02", "bronze_age");

sh.addTagRange("jade_monitor.jade_artifacts", {"era": "neolithic_hongshan"}, {"era": "neolithic_liangzhu"}, "neolithic");
sh.addTagRange("jade_monitor.jade_artifacts", {"era": "shang"}, {"era": "western_zhou"}, "bronze_age");

print("MongoDB sharding by era configured successfully.");
