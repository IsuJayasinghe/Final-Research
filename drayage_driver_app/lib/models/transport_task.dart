/// Operational status of a container transport task inside the port.
enum TaskStatus {
  assigned,
  accepted,
  travellingToPickup,
  atPickup,
  inTransit,
  atDestination,
  completed,
  cancelled,
}

extension TaskStatusExtension on TaskStatus {
  String get displayName {
    switch (this) {
      case TaskStatus.assigned:
        return 'Assigned';
      case TaskStatus.accepted:
        return 'Accepted';
      case TaskStatus.travellingToPickup:
        return 'Travelling to Pickup';
      case TaskStatus.atPickup:
        return 'At Pickup';
      case TaskStatus.inTransit:
        return 'In Transit';
      case TaskStatus.atDestination:
        return 'At Destination';
      case TaskStatus.completed:
        return 'Completed';
      case TaskStatus.cancelled:
        return 'Cancelled';
    }
  }

  /// Returns the next recommended status in the canonical port lifecycle
  TaskStatus? get nextStatus {
    switch (this) {
      case TaskStatus.assigned:
        return TaskStatus.accepted;
      case TaskStatus.accepted:
        return TaskStatus.travellingToPickup;
      case TaskStatus.travellingToPickup:
        return TaskStatus.atPickup;
      case TaskStatus.atPickup:
        return TaskStatus.inTransit;
      case TaskStatus.inTransit:
        return TaskStatus.atDestination;
      case TaskStatus.atDestination:
        return TaskStatus.completed;
      case TaskStatus.completed:
      case TaskStatus.cancelled:
        return null;
    }
  }

  /// List of valid status transitions from the current state
  List<TaskStatus> get allowedTransitions {
    switch (this) {
      case TaskStatus.assigned:
        return [TaskStatus.accepted, TaskStatus.cancelled];
      case TaskStatus.accepted:
        return [TaskStatus.travellingToPickup, TaskStatus.cancelled];
      case TaskStatus.travellingToPickup:
        return [TaskStatus.atPickup, TaskStatus.cancelled];
      case TaskStatus.atPickup:
        return [TaskStatus.inTransit, TaskStatus.cancelled];
      case TaskStatus.inTransit:
        return [TaskStatus.atDestination, TaskStatus.cancelled];
      case TaskStatus.atDestination:
        return [TaskStatus.completed];
      case TaskStatus.completed:
      case TaskStatus.cancelled:
        return [];
    }
  }

  bool canTransitionTo(TaskStatus target) {
    return allowedTransitions.contains(target);
  }

  static TaskStatus fromString(String value) {
    return TaskStatus.values.firstWhere(
      (s) =>
          s.name.toLowerCase() ==
          value.toLowerCase().replaceAll('_', '').replaceAll(' ', ''),
      orElse: () => TaskStatus.assigned,
    );
  }
}

/// Priority rating assigned by the Intelligent Optimization Engine.
enum TaskPriority { low, normal, high, urgent }

extension TaskPriorityExtension on TaskPriority {
  String get displayName {
    switch (this) {
      case TaskPriority.low:
        return 'Low';
      case TaskPriority.normal:
        return 'Normal';
      case TaskPriority.high:
        return 'High';
      case TaskPriority.urgent:
        return 'Urgent';
    }
  }

  static TaskPriority fromString(String value) {
    return TaskPriority.values.firstWhere(
      (p) => p.name.toLowerCase() == value.toLowerCase(),
      orElse: () => TaskPriority.normal,
    );
  }
}

/// Model representing a container transport task dispatched by Component 2.
class TransportTask {
  final String id;
  final String containerId;
  final String containerSize; // e.g. 20ft, 40ft, 45ft HC
  final String containerType; // Dry, Reefer, HazMat
  final String pickupZone;
  final String destinationZone;
  final TaskPriority priority;
  final TaskStatus status;
  final DateTime assignedAt;
  final DateTime? completedAt;
  final String instructions;
  final double estimatedDistanceKm;
  final int estimatedTimeMinutes;
  final String? assignedTruckId;

  const TransportTask({
    required this.id,
    required this.containerId,
    required this.containerSize,
    required this.containerType,
    required this.pickupZone,
    required this.destinationZone,
    required this.priority,
    required this.status,
    required this.assignedAt,
    this.completedAt,
    required this.instructions,
    required this.estimatedDistanceKm,
    required this.estimatedTimeMinutes,
    this.assignedTruckId,
  });

  bool get isActive =>
      status != TaskStatus.completed && status != TaskStatus.cancelled;

  TransportTask copyWith({
    String? id,
    String? containerId,
    String? containerSize,
    String? containerType,
    String? pickupZone,
    String? destinationZone,
    TaskPriority? priority,
    TaskStatus? status,
    DateTime? assignedAt,
    DateTime? completedAt,
    String? instructions,
    double? estimatedDistanceKm,
    int? estimatedTimeMinutes,
    String? assignedTruckId,
  }) {
    return TransportTask(
      id: id ?? this.id,
      containerId: containerId ?? this.containerId,
      containerSize: containerSize ?? this.containerSize,
      containerType: containerType ?? this.containerType,
      pickupZone: pickupZone ?? this.pickupZone,
      destinationZone: destinationZone ?? this.destinationZone,
      priority: priority ?? this.priority,
      status: status ?? this.status,
      assignedAt: assignedAt ?? this.assignedAt,
      completedAt: completedAt ?? this.completedAt,
      instructions: instructions ?? this.instructions,
      estimatedDistanceKm: estimatedDistanceKm ?? this.estimatedDistanceKm,
      estimatedTimeMinutes: estimatedTimeMinutes ?? this.estimatedTimeMinutes,
      assignedTruckId: assignedTruckId ?? this.assignedTruckId,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'containerId': containerId,
        'containerSize': containerSize,
        'containerType': containerType,
        'pickupZone': pickupZone,
        'destinationZone': destinationZone,
        'priority': priority.name,
        'status': status.name,
        'assignedAt': assignedAt.toIso8601String(),
        'completedAt': completedAt?.toIso8601String(),
        'instructions': instructions,
        'estimatedDistanceKm': estimatedDistanceKm,
        'estimatedTimeMinutes': estimatedTimeMinutes,
        'assignedTruckId': assignedTruckId,
      };

  factory TransportTask.fromJson(Map<String, dynamic> json) => TransportTask(
        id: json['id'] as String,
        containerId: (json['containerId'] ?? json['container_id']) as String? ??
            'CONT-001',
        containerSize:
            (json['containerSize'] ?? json['container_iso']) as String? ??
                '40ft',
        containerType:
            (json['containerType'] ?? json['container_type']) as String? ??
                'Dry',
        pickupZone:
            (json['pickupZone'] ?? json['pickup_zone']) as String? ?? 'Pickup',
        destinationZone:
            (json['destinationZone'] ?? json['destination_zone']) as String? ??
                'Destination',
        priority: TaskPriorityExtension.fromString(
          json['priority'] as String? ?? 'normal',
        ),
        status: TaskStatusExtension.fromString(json['status'] as String),
        assignedAt: json['assignedAt'] != null
            ? DateTime.parse(json['assignedAt'] as String)
            : json['created_at'] != null
                ? DateTime.parse(json['created_at'] as String)
                : DateTime.now(),
        completedAt: json['completedAt'] != null
            ? DateTime.parse(json['completedAt'] as String)
            : json['completed_at'] != null
                ? DateTime.parse(json['completed_at'] as String)
                : null,
        instructions:
            (json['instructions'] ?? json['special_instructions']) as String? ??
                '',
        estimatedDistanceKm: ((json['estimatedDistanceKm'] ??
                    (json['distance_meters'] != null
                        ? (json['distance_meters'] as num) / 1000.0
                        : null)) as num?)
                ?.toDouble() ??
            1.2,
        estimatedTimeMinutes: ((json['estimatedTimeMinutes'] ??
                    json['estimated_travel_minutes']) as num?)
                ?.round() ??
            15,
        assignedTruckId:
            (json['assignedTruckId'] ?? json['assigned_truck_id']) as String?,
      );
}
