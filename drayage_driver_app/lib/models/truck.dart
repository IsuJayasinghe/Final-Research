/// Status of a port internal terminal truck.
enum TruckStatus {
  available,
  assigned,
  travellingToPickup,
  atPickup,
  inTransit,
  atDestination,
  completed,
  unavailable,
}

extension TruckStatusExtension on TruckStatus {
  String get displayName {
    switch (this) {
      case TruckStatus.available:
        return 'Available';
      case TruckStatus.assigned:
        return 'Assigned';
      case TruckStatus.travellingToPickup:
        return 'Travelling to Pickup';
      case TruckStatus.atPickup:
        return 'At Pickup';
      case TruckStatus.inTransit:
        return 'In Transit';
      case TruckStatus.atDestination:
        return 'At Destination';
      case TruckStatus.completed:
        return 'Completed';
      case TruckStatus.unavailable:
        return 'Unavailable';
    }
  }

  static TruckStatus fromString(String value) {
    return TruckStatus.values.firstWhere(
      (s) => s.name.toLowerCase() == value.toLowerCase().replaceAll(' ', ''),
      orElse: () => TruckStatus.available,
    );
  }
}

/// Model representing a terminal drayage truck.
class Truck {
  final String id;
  final String licensePlate;
  final String model;
  final double fuelLevelPercentage;
  final TruckStatus status;
  final String currentZone;

  const Truck({
    required this.id,
    required this.licensePlate,
    required this.model,
    required this.fuelLevelPercentage,
    required this.status,
    required this.currentZone,
  });

  Truck copyWith({
    String? id,
    String? licensePlate,
    String? model,
    double? fuelLevelPercentage,
    TruckStatus? status,
    String? currentZone,
  }) {
    return Truck(
      id: id ?? this.id,
      licensePlate: licensePlate ?? this.licensePlate,
      model: model ?? this.model,
      fuelLevelPercentage: fuelLevelPercentage ?? this.fuelLevelPercentage,
      status: status ?? this.status,
      currentZone: currentZone ?? this.currentZone,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'licensePlate': licensePlate,
        'model': model,
        'fuelLevelPercentage': fuelLevelPercentage,
        'status': status.name,
        'currentZone': currentZone,
      };

  factory Truck.fromJson(Map<String, dynamic> json) => Truck(
        id: json['id'] as String,
        licensePlate: json['licensePlate'] as String,
        model: json['model'] as String,
        fuelLevelPercentage: (json['fuelLevelPercentage'] as num).toDouble(),
        status: TruckStatusExtension.fromString(json['status'] as String),
        currentZone: json['currentZone'] as String,
      );
}
