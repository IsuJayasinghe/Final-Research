import '../models/transport_task.dart';
import '../core/config/app_config.dart';
import '../core/errors/app_exceptions.dart';
import '../core/network/api_client.dart';
import 'mock_data_service.dart';

/// Task Service managing transport assignments dispatched by Component 2.
/// Interfaces with Python/FastAPI `/api/v1/tasks/*` in live mode,
/// and uses validated development mock tasks for offline fallback.
class TaskService {
  final ApiClient _apiClient;

  TaskService({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  /// Fetch all active tasks for the currently assigned driver/truck
  Future<List<TransportTask>> getActiveTasks() async {
    if (!AppConfig.useMockData) {
      try {
        final response = await _apiClient.get('/tasks/assigned');
        final list = response as List<dynamic>;
        return list
            .map((item) => TransportTask.fromJson(item as Map<String, dynamic>))
            .toList();
      } catch (e) {
        // Fallback to mock data if network fails
        return MockDataService.getActiveTasks();
      }
    }
    await Future.delayed(const Duration(milliseconds: 200));
    return MockDataService.getActiveTasks();
  }

  /// Fetch completed task history
  Future<List<TransportTask>> getCompletedTasks() async {
    if (!AppConfig.useMockData) {
      try {
        final response = await _apiClient.get('/tasks/history');
        final list = response as List<dynamic>;
        return list
            .map((item) => TransportTask.fromJson(item as Map<String, dynamic>))
            .toList();
      } catch (e) {
        return MockDataService.getCompletedTasks();
      }
    }
    await Future.delayed(const Duration(milliseconds: 200));
    return MockDataService.getCompletedTasks();
  }

  /// Fetch specific task by ID
  Future<TransportTask> getTaskById(String taskId) async {
    if (!AppConfig.useMockData) {
      try {
        final response = await _apiClient.get('/tasks/$taskId');
        return TransportTask.fromJson(response as Map<String, dynamic>);
      } catch (e) {
        final task = MockDataService.getTaskById(taskId);
        if (task != null) return task;
        throw AppException('Task $taskId not found in system.');
      }
    }
    final task = MockDataService.getTaskById(taskId);
    if (task == null) {
      throw AppException('Task $taskId not found in system.');
    }
    return task;
  }

  /// Update the status of a task following strict operational state machine rules:
  /// ASSIGNED -> ACCEPTED -> TRAVELLING_TO_PICKUP -> AT_PICKUP -> IN_TRANSIT -> AT_DESTINATION -> COMPLETED
  Future<TransportTask> updateTaskStatus(
    String taskId,
    TaskStatus targetStatus,
  ) async {
    if (!AppConfig.useMockData) {
      try {
        final response = await _apiClient.patch(
          '/tasks/$taskId/status',
          body: {'status': targetStatus.name},
        );
        return TransportTask.fromJson(response as Map<String, dynamic>);
      } catch (e) {
        if (e is TaskTransitionException) rethrow;
      }
    }

    final existing = MockDataService.getTaskById(taskId);
    if (existing == null) {
      throw AppException('Task $taskId was not found.');
    }

    if (!existing.status.canTransitionTo(targetStatus) &&
        targetStatus != TaskStatus.cancelled) {
      throw TaskTransitionException(
        'Invalid transition from ${existing.status.displayName} to ${targetStatus.displayName}.',
      );
    }

    final success = MockDataService.updateTaskStatus(taskId, targetStatus);
    if (!success) {
      throw const TaskTransitionException(
        'Failed to update task status in backend.',
      );
    }

    return MockDataService.getTaskById(taskId)!;
  }
}
