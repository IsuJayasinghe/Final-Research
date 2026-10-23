import 'package:flutter/material.dart';

import '../../services/notification_service.dart';
import '../../app/theme.dart';
import '../../core/utils/date_formatter.dart';

/// Screen displaying operational and optimization dispatch notifications for the driver.
class NotificationsScreen extends StatefulWidget {
  final NotificationService notificationService;

  const NotificationsScreen({
    super.key,
    required this.notificationService,
  });

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<DriverNotification> _notifications = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() {
      _isLoading = true;
    });

    final items = await widget.notificationService.getNotifications();

    setState(() {
      _notifications = items;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: const Text('Notifications & Alerts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadNotifications,
            tooltip: 'Refresh Notifications',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.portAmber),
            )
          : _notifications.isEmpty
              ? const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.notifications_off_outlined,
                        color: AppTheme.textSecondary,
                        size: 48,
                      ),
                      SizedBox(height: 12),
                      Text(
                        'No New Notifications',
                        style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      SizedBox(height: 6),
                      Text(
                        'You are up to date with dispatch operations.',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _notifications.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final item = _notifications[index];
                    final isTaskAlert = item.relatedTaskId != null;

                    return Card(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: isTaskAlert
                            ? () {
                                Navigator.of(context).pushNamed(
                                  '/task-details',
                                  arguments: item.relatedTaskId,
                                );
                              }
                            : null,
                        child: Padding(
                          padding: const EdgeInsets.all(14.0),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                width: 38,
                                height: 38,
                                decoration: BoxDecoration(
                                  color: isTaskAlert
                                      ? AppTheme.portAmber
                                          .withValues(alpha: 0.15)
                                      : AppTheme.portCyan
                                          .withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Icon(
                                  isTaskAlert
                                      ? Icons.assignment_outlined
                                      : Icons.info_outline,
                                  color: isTaskAlert
                                      ? AppTheme.portAmber
                                      : AppTheme.portCyan,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.title,
                                            style: const TextStyle(
                                              color: AppTheme.textPrimary,
                                              fontSize: 14,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                        Text(
                                          DateFormatter.formatTime(
                                              item.timestamp),
                                          style: const TextStyle(
                                            color: AppTheme.textSecondary,
                                            fontSize: 11,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      item.message,
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 13,
                                        height: 1.3,
                                      ),
                                    ),
                                    if (isTaskAlert) ...[
                                      const SizedBox(height: 8),
                                      Row(
                                        children: [
                                          Text(
                                            'View ${item.relatedTaskId} details',
                                            style: const TextStyle(
                                              color: AppTheme.portCyan,
                                              fontSize: 12,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          const SizedBox(width: 4),
                                          const Icon(
                                            Icons.arrow_forward_ios,
                                            size: 10,
                                            color: AppTheme.portCyan,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
