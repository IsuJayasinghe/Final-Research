import 'package:flutter_test/flutter_test.dart';
import 'package:drayage_driver_app/models/driver.dart';
import 'package:drayage_driver_app/models/truck.dart';
import 'package:drayage_driver_app/models/transport_task.dart';
import 'package:drayage_driver_app/models/location_update.dart';
import 'package:drayage_driver_app/services/mock_data_service.dart';
import 'package:drayage_driver_app/services/auth_service.dart';
import 'package:drayage_driver_app/services/task_service.dart';
import 'package:drayage_driver_app/services/notification_service.dart';
import 'package:drayage_driver_app/core/network/api_client.dart';

void main() {
  group('Component 2 Domain Model Tests', () {
    test('TaskStatus transitions strictly follow operational lifecycle', () {
      expect(TaskStatus.assigned.canTransitionTo(TaskStatus.accepted), isTrue);
      expect(
        TaskStatus.accepted.canTransitionTo(TaskStatus.travellingToPickup),
        isTrue,
      );
      expect(
        TaskStatus.travellingToPickup.canTransitionTo(TaskStatus.atPickup),
        isTrue,
      );
      expect(TaskStatus.atPickup.canTransitionTo(TaskStatus.inTransit), isTrue);
      expect(
        TaskStatus.inTransit.canTransitionTo(TaskStatus.atDestination),
        isTrue,
      );
      expect(
        TaskStatus.atDestination.canTransitionTo(TaskStatus.completed),
        isTrue,
      );

      // Verify invalid transitions are prevented
      expect(
        TaskStatus.assigned.canTransitionTo(TaskStatus.completed),
        isFalse,
      );
      expect(
        TaskStatus.completed.canTransitionTo(TaskStatus.accepted),
        isFalse,
      );
    });

    test('Truck model serialization and deserialization', () {
      const truck = MockDataService.sampleTruck;
      final json = truck.toJson();
      expect(json['id'], 'TRK-025');
      expect(json['status'], 'assigned');

      final deserialized = Truck.fromJson(json);
      expect(deserialized.id, truck.id);
      expect(deserialized.licensePlate, truck.licensePlate);
      expect(deserialized.status, TruckStatus.assigned);
    });

    test('Driver duty status toggles correctly', () {
      const driver = MockDataService.sampleDriver;
      expect(driver.dutyStatus, DriverDutyStatus.onDuty);

      final onBreak = driver.copyWith(dutyStatus: DriverDutyStatus.onBreak);
      expect(onBreak.dutyStatus, DriverDutyStatus.onBreak);
    });
  });

  group('Component 2 Services & Lifecycle Tests', () {
    late AuthService authService;
    late TaskService taskService;

    setUp(() {
      authService = AuthService();
      taskService = TaskService();
    });

    test('AuthService logs in driver with valid credentials', () async {
      final driver = await authService.login('DRV-102', 'drayage2026');
      expect(driver.id, 'DRV-102');
      expect(authService.isAuthenticated, isTrue);
    });

    test('AuthService rejects empty or invalid credentials', () async {
      expect(
        () async => await authService.login('', ''),
        throwsA(isA<Exception>()),
      );
    });

    test(
      'TaskService fetches active assignments and completed history',
      () async {
        final active = await taskService.getActiveTasks();
        expect(active, isNotEmpty);
        expect(active.every((t) => t.isActive), isTrue);

        final completed = await taskService.getCompletedTasks();
        expect(completed, isNotEmpty);
        expect(
          completed.every((t) => t.status == TaskStatus.completed),
          isTrue,
        );
      },
    );

    test(
      'TaskService updates task status following permitted transition',
      () async {
        final active = await taskService.getActiveTasks();
        final task = active.first;
        final nextStatus = task.status.nextStatus;

        if (nextStatus != null) {
          final updated = await taskService.updateTaskStatus(
            task.id,
            nextStatus,
          );
          expect(updated.status, nextStatus);
        }
      },
    );

    test('NotificationService delivers operational dispatch alerts', () async {
      final notifService = NotificationService();
      final notifications = await notifService.getNotifications();
      expect(notifications, isNotEmpty);
      expect(notifications.any((n) => n.relatedTaskId == 'TASK-501'), isTrue);
    });

    test('ApiClient configures bearer authentication correctly', () {
      final client = ApiClient();
      expect(client.isAuthenticated, isFalse);
      client.setAuthToken('mock-jwt-token-xyz');
      expect(client.isAuthenticated, isTrue);
      client.clearAuthToken();
      expect(client.isAuthenticated, isFalse);
      client.close();
    });

    test('LocationUpdate model serialization handles GPS coordinates', () {
      final update = LocationUpdate(
        truckId: 'TRK-025',
        driverId: 'DRV-102',
        latitude: 6.9428,
        longitude: 79.8452,
        speedKmh: 18.5,
        headingDegrees: 84.0,
        accuracyMeters: 0.3,
        timestamp: DateTime(2026, 10, 22, 7, 0),
        currentZone: 'Berth B03',
      );

      final json = update.toJson();
      expect(json['truckId'], 'TRK-025');
      expect(json['latitude'], 6.9428);

      final deserialized = LocationUpdate.fromJson(json);
      expect(deserialized.truckId, update.truckId);
      expect(deserialized.latitude, update.latitude);
      expect(deserialized.currentZone, 'Berth B03');
    });
  });
}
