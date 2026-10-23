/// Driver availability / duty status inside the port.
enum DriverDutyStatus { onDuty, onBreak, offDuty }

extension DriverDutyStatusExtension on DriverDutyStatus {
  String get displayName {
    switch (this) {
      case DriverDutyStatus.onDuty:
        return 'On Duty';
      case DriverDutyStatus.onBreak:
        return 'On Break';
      case DriverDutyStatus.offDuty:
        return 'Off Duty';
    }
  }
}

/// Model representing an authenticated terminal truck driver.
class Driver {
  final String id;
  final String name;
  final String email;
  final String phoneNumber;
  final String licenseNumber;
  final String assignedTruckId;
  final DriverDutyStatus dutyStatus;
  final String shift; // e.g. "Morning Shift (06:00 - 14:00)"
  final int totalCompletedTasksToday;

  const Driver({
    required this.id,
    required this.name,
    required this.email,
    required this.phoneNumber,
    required this.licenseNumber,
    required this.assignedTruckId,
    required this.dutyStatus,
    required this.shift,
    this.totalCompletedTasksToday = 0,
  });

  Driver copyWith({
    String? id,
    String? name,
    String? email,
    String? phoneNumber,
    String? licenseNumber,
    String? assignedTruckId,
    DriverDutyStatus? dutyStatus,
    String? shift,
    int? totalCompletedTasksToday,
  }) {
    return Driver(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      licenseNumber: licenseNumber ?? this.licenseNumber,
      assignedTruckId: assignedTruckId ?? this.assignedTruckId,
      dutyStatus: dutyStatus ?? this.dutyStatus,
      shift: shift ?? this.shift,
      totalCompletedTasksToday:
          totalCompletedTasksToday ?? this.totalCompletedTasksToday,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'email': email,
        'phoneNumber': phoneNumber,
        'licenseNumber': licenseNumber,
        'assignedTruckId': assignedTruckId,
        'dutyStatus': dutyStatus.name,
        'shift': shift,
        'totalCompletedTasksToday': totalCompletedTasksToday,
      };

  factory Driver.fromJson(Map<String, dynamic> json) => Driver(
        id: json['id'] as String,
        name: json['name'] as String,
        email: json['email'] as String? ??
            '${(json['id'] as String).toLowerCase()}@port.local',
        phoneNumber: (json['phoneNumber'] ?? json['phone']) as String? ??
            '+94 77 123 4567',
        licenseNumber: json['licenseNumber'] as String? ?? 'LIC-SL-8849',
        assignedTruckId:
            (json['assignedTruckId'] ?? json['assigned_truck_id']) as String? ??
                'TRK-025',
        dutyStatus: DriverDutyStatus.values.firstWhere(
          (d) =>
              d.name.toLowerCase() ==
              (json['dutyStatus'] ?? json['duty_status'] ?? '')
                  .toString()
                  .toLowerCase(),
          orElse: () => DriverDutyStatus.onDuty,
        ),
        shift: json['shift'] as String? ?? 'Morning Shift (06:00 - 14:00)',
        totalCompletedTasksToday:
            (json['totalCompletedTasksToday'] as num?)?.toInt() ?? 0,
      );
}
