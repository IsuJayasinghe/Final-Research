/// Notification event for terminal truck drivers
class DriverNotification {
  final String id;
  final String title;
  final String message;
  final DateTime timestamp;
  final bool isRead;
  final String? relatedTaskId;

  const DriverNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.timestamp,
    this.isRead = false,
    this.relatedTaskId,
  });
}

class NotificationService {
  final List<DriverNotification> _notifications = [
    DriverNotification(
      id: 'NOTIF-01',
      title: 'New High Priority Task Dispatched',
      message: 'Optimization engine assigned TASK-501 (Berth B03 -> Yard Y12).',
      timestamp: DateTime.now().subtract(const Duration(minutes: 12)),
      relatedTaskId: 'TASK-501',
    ),
    DriverNotification(
      id: 'NOTIF-02',
      title: 'Terminal Traffic Alert',
      message:
          'Congestion reported on Quayside Way. Recommended diversion via Arterial 2.',
      timestamp: DateTime.now().subtract(const Duration(minutes: 35)),
    ),
    DriverNotification(
      id: 'NOTIF-03',
      title: 'Task TASK-498 Confirmed Completed',
      message:
          'Yard staff confirmed container MEDU-332910-8 stacked safely in Yard Y07.',
      timestamp: DateTime.now().subtract(const Duration(hours: 1, minutes: 35)),
      relatedTaskId: 'TASK-498',
    ),
  ];

  Future<List<DriverNotification>> getNotifications() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return List.unmodifiable(_notifications);
  }
}
