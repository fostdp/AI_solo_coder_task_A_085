conn = new Mongo();
db = conn.getDB("jade_monitor");

db.createCollection("jade_artifacts");
db.jade_artifacts.createIndex({ artifact_id: 1 }, { unique: true });
db.jade_artifacts.createIndex({ culture: 1 });

db.createCollection("spectrum_data");
db.spectrum_data.createIndex({ artifact_id: 1, timestamp: -1 });
db.spectrum_data.createIndex({ device_id: 1 });

db.createCollection("raman_spectrum");
db.raman_spectrum.createIndex({ artifact_id: 1, timestamp: -1 });

db.createCollection("xrf_spectrum");
db.xrf_spectrum.createIndex({ artifact_id: 1, timestamp: -1 });

db.createCollection("diffusion_results");
db.diffusion_results.createIndex({ artifact_id: 1, timestamp: -1 });

db.createCollection("anomaly_results");
db.anomaly_results.createIndex({ artifact_id: 1, timestamp: -1 });

db.createCollection("alerts");
db.alerts.createIndex({ artifact_id: 1, timestamp: -1 });
db.alerts.createIndex({ status: 1 });

db.createCollection("devices");
db.devices.createIndex({ device_id: 1 }, { unique: true });

var cultures = ["红山文化", "良渚文化"];
var jadeTypes = ["玉璧", "玉琮", "玉钺", "玉璜", "玉珠", "玉管", "玉兽", "玉鸟"];
var images = [
    "jade_bi.png", "jade_cong.png", "jade_yue.png", "jade_huang.png",
    "jade_zhu.png", "jade_guan.png", "jade_shou.png", "jade_niao.png"
];

for (var i = 1; i <= 200; i++) {
    var culture = cultures[i % 2];
    var jadeType = jadeTypes[i % jadeTypes.length];
    var image = images[i % images.length];
    var isForgery = Math.random() < 0.15;
    
    db.jade_artifacts.insertOne({
        artifact_id: "JD" + String(i).padStart(4, "0"),
        name: culture + jadeType + "-" + i,
        culture: culture,
        jade_type: jadeType,
        image_file: image,
        excavation_site: culture === "红山文化" ? "牛河梁遗址" : "反山遗址",
        excavation_year: 2010 + (i % 15),
        description: "出土于" + (culture === "红山文化" ? "辽宁朝阳" : "浙江余杭") + "的典型" + jadeType,
        size: {
            length: 5 + Math.random() * 15,
            width: 3 + Math.random() * 10,
            thickness: 0.5 + Math.random() * 2
        },
        weight: 50 + Math.random() * 500,
        is_suspected_forgery: isForgery,
        create_time: new Date(),
        update_time: new Date()
    });
}

for (var i = 1; i <= 20; i++) {
    db.devices.insertOne({
        device_id: "RAMAN" + String(i).padStart(3, "0"),
        device_type: "raman",
        model: "Renishaw-inVia",
        status: "online",
        location: "实验室A区-" + i,
        last_heartbeat: new Date()
    });
}

for (var i = 1; i <= 20; i++) {
    db.devices.insertOne({
        device_id: "XRF" + String(i).padStart(3, "0"),
        device_type: "xrf",
        model: "Bruker-S8",
        status: "online",
        location: "实验室B区-" + i,
        last_heartbeat: new Date()
    });
}

print("数据库初始化完成：200件玉器，40台设备");
