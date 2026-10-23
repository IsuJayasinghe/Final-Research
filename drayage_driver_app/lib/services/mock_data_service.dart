import '../models/driver.dart';
import '../models/truck.dart';
import '../models/transport_task.dart';
import '../models/location_update.dart';

/// Centralized mock data repository for Component 2 offline development and UI verification.
/// Matches the research scenario for port internal terminal truck operations.
class MockDataService {
  static const Driver sampleDriver = Driver(
    id: 'DRV-102',
    name: 'Marcus Vance',
    email: 'marcus.vance@portops.local',
    phoneNumber: '+1 (555) 019-4822',
    licenseNumber: 'CDL-TRK-88291',
    assignedTruckId: 'TRK-025',
    dutyStatus: DriverDutyStatus.onDuty,
    shift: 'Day Shift (06:00 - 18:00)',
    totalCompletedTasksToday: 4,
  );

  static const Truck sampleTruck = Truck(
    id: 'TRK-025',
    licensePlate: 'PORT-TK-25',
    model: 'Kalmar Ottawa T2 Terminal Tractor',
    fuelLevelPercentage: 78.5,
    status: TruckStatus.assigned,
    currentZone: 'Buffer Area B-02',
  );

  static final List<TransportTask> _tasks = [
    TransportTask(
      id: 'TASK-501',
      containerId: 'MSKU-782910-4',
      containerSize: '40ft HC',
      containerType: 'Dry Cargo',
      pickupZone: 'Berth B03 (Quayside Gantry QG-04)',
      destinationZone: 'Yard Y12 (Stack Bay S-08)',
      priority: TaskPriority.high,
      status: TaskStatus.assigned,
      assignedAt: DateTime.now().subtract(const Duration(minutes: 12)),
      instructions:
          'Proceed to Berth B03. Coordinate with Crane Operator QG-04. Secure twistlocks before departing quay.',
      estimatedDistanceKm: 1.8,
      estimatedTimeMinutes: 7,
      assignedTruckId: 'TRK-025',
    ),
    TransportTask(
      id: 'TASK-502',
      containerId: 'CMAU-991204-1',
      containerSize: '20ft',
      containerType: 'Reefer (Active)',
      pickupZone: 'Yard Y04 (Reefer Rack R-02)',
      destinationZone: 'Berth B01 (Ship CMA CGM Pegasus)',
      priority: TaskPriority.urgent,
      status: TaskStatus.assigned,
      assignedAt: DateTime.now().subtract(const Duration(minutes: 4)),
      instructions:
          'Urgent loading sequence for vessel outbound. Reefer unplugged at 03:45 UTC. Maintain direct line via Arterial 1.',
      estimatedDistanceKm: 2.4,
      estimatedTimeMinutes: 9,
      assignedTruckId: 'TRK-025',
    ),
    TransportTask(
      id: 'TASK-498',
      containerId: 'MEDU-332910-8',
      containerSize: '45ft High Cube',
      containerType: 'Dry Cargo',
      pickupZone: 'Gate Interchange Lane 03',
      destinationZone: 'Yard Y07 (Import Block)',
      priority: TaskPriority.normal,
      status: TaskStatus.completed,
      assignedAt: DateTime.now().subtract(
        const Duration(hours: 2, minutes: 15),
      ),
      completedAt: DateTime.now().subtract(
        const Duration(hours: 1, minutes: 35),
      ),
      instructions:
          'Gate inbound transfer completed. Stacked in Yard Y07 Row 14 Tier 2.',
      estimatedDistanceKm: 1.4,
      estimatedTimeMinutes: 6,
      assignedTruckId: 'TRK-025',
    ),
    TransportTask(
      id: 'TASK-495',
      containerId: 'HLXU-102847-5',
      containerSize: '40ft Reefer',
      containerType: 'Reefer',
      pickupZone: 'Berth B02',
      destinationZone: 'Yard Y04 (Reefer Area)',
      priority: TaskPriority.high,
      status: TaskStatus.completed,
      assignedAt: DateTime.now().subtract(
        const Duration(hours: 3, minutes: 40),
      ),
      completedAt: DateTime.now().subtract(
        const Duration(hours: 2, minutes: 55),
      ),
      instructions:
          'Discharged from vessel MV Pacific Glory. Reefer plug-in confirmed by yard staff.',
      estimatedDistanceKm: 2.1,
      estimatedTimeMinutes: 8,
      assignedTruckId: 'TRK-025',
    ),
    TransportTask(
      id: 'TASK-492',
      containerId: 'TEMU-837192-3',
      containerSize: '20ft',
      containerType: 'HazMat (Class 3 Flammable)',
      pickupZone: 'Yard Y19 (HazMat Zone)',
      destinationZone: 'Rail Transfer Siding 2',
      priority: TaskPriority.urgent,
      status: TaskStatus.completed,
      assignedAt: DateTime.now().subtract(const Duration(hours: 5)),
      completedAt: DateTime.now().subtract(
        const Duration(hours: 4, minutes: 15),
      ),
      instructions:
          'Speed limit strictly 15 km/h. HazMat escort required near Rail Siding 2.',
      estimatedDistanceKm: 3.2,
      estimatedTimeMinutes: 14,
      assignedTruckId: 'TRK-025',
    ),
  ];

  static List<TransportTask> getAllTasks() => List.unmodifiable(_tasks);

  static List<TransportTask> getActiveTasks() =>
      _tasks.where((t) => t.isActive).toList();

  static List<TransportTask> getCompletedTasks() =>
      _tasks.where((t) => t.status == TaskStatus.completed).toList();

  static TransportTask? getTaskById(String taskId) {
    try {
      return _tasks.firstWhere((t) => t.id == taskId);
    } catch (_) {
      return null;
    }
  }

  static bool updateTaskStatus(String taskId, TaskStatus newStatus) {
    final index = _tasks.indexWhere((t) => t.id == taskId);
    if (index == -1) return false;

    final currentTask = _tasks[index];
    if (!currentTask.status.canTransitionTo(newStatus) &&
        newStatus != TaskStatus.cancelled) {
      return false;
    }

    _tasks[index] = currentTask.copyWith(
      status: newStatus,
      completedAt: newStatus == TaskStatus.completed
          ? DateTime.now()
          : currentTask.completedAt,
    );
    return true;
  }

  static LocationUpdate getMockLocation() {
    return LocationUpdate(
      truckId: sampleTruck.id,
      driverId: sampleDriver.id,
      latitude: 6.9428,
      longitude: 79.8450,
      speedKmh: 18.5,
      headingDegrees: 45.0,
      accuracyMeters: 3.2,
      timestamp: DateTime.now(),
      currentZone: 'Terminal Arterial Road 2',
    );
  }
}
