/// Location coordinate record for internal port truck tracking.
class LocationUpdate {
  final String truckId;
  final String driverId;
  final double latitude;
  final double longitude;
  final double? speedKmh;
  final double? headingDegrees;
  final double? accuracyMeters;
  final DateTime timestamp;
  final String? currentZone;

  const LocationUpdate({
    required this.truckId,
    required this.driverId,
    required this.latitude,
    required this.longitude,
    this.speedKmh,
    this.headingDegrees,
    this.accuracyMeters,
    required this.timestamp,
    this.currentZone,
  });

  Map<String, dynamic> toJson() => {
        'truckId': truckId,
        'driverId': driverId,
        'latitude': latitude,
        'longitude': longitude,
        'speedKmh': speedKmh,
        'headingDegrees': headingDegrees,
        'accuracyMeters': accuracyMeters,
        'timestamp': timestamp.toIso8601String(),
        'currentZone': currentZone,
      };

  factory LocationUpdate.fromJson(Map<String, dynamic> json) => LocationUpdate(
        truckId: json['truckId'] as String,
        driverId: json['driverId'] as String,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        speedKmh: (json['speedKmh'] as num?)?.toDouble(),
        headingDegrees: (json['headingDegrees'] as num?)?.toDouble(),
        accuracyMeters: (json['accuracyMeters'] as num?)?.toDouble(),
        timestamp: DateTime.parse(json['timestamp'] as String),
        currentZone: json['currentZone'] as String?,
      );
}
