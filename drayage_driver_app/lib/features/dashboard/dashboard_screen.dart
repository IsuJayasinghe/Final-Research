import 'package:flutter/material.dart';

import '../../models/driver.dart';
import '../../models/truck.dart';
import '../../models/transport_task.dart';
import '../../services/auth_service.dart';
import '../../services/task_service.dart';
import '../../services/notification_service.dart';
import '../../services/mock_data_service.dart';
import '../../app/theme.dart';
import '../../app/routes.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/info_card.dart';
import '../../widgets/loading_indicator.dart';
import '../tasks/widgets/task_status_dialog.dart';

class DashboardScreen extends StatefulWidget {
  final AuthService authService;
  final TaskService taskService;
  final NotificationService? notificationService;

  const DashboardScreen({
    super.key,
    required this.authService,
    required this.taskService,
    this.notificationService,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Driver? _driver;
  final Truck _truck = MockDataService.sampleTruck;
  List<TransportTask> _activeTasks = [];
  bool _isLoading = true;
  bool _isUpdatingStatus = false;
  int _unreadNotifications = 0;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() {
      _isLoading = true;
    });

    _driver = widget.authService.currentDriver ?? MockDataService.sampleDriver;
    final active = await widget.taskService.getActiveTasks();

    int unread = 0;
    if (widget.notificationService != null) {
      final notifs = await widget.notificationService!.getNotifications();
      unread = notifs.where((n) => !n.isRead).length;
    }

    setState(() {
      _activeTasks = active;
      _unreadNotifications = unread;
      _isLoading = false;
    });
  }

  String _getNextStatusActionLabel(TaskStatus status) {
    switch (status) {
      case TaskStatus.assigned:
        return 'ACCEPT MISSION';
      case TaskStatus.accepted:
        return 'START TRIP TO PICKUP';
      case TaskStatus.travellingToPickup:
        return 'ARRIVED AT PICKUP';
      case TaskStatus.atPickup:
        return 'CONFIRM LOAD & START TRANSIT';
      case TaskStatus.inTransit:
        return 'ARRIVED AT DESTINATION';
      case TaskStatus.atDestination:
        return 'COMPLETE MISSION';
      case TaskStatus.completed:
      case TaskStatus.cancelled:
        return 'MISSION CLOSED';
    }
  }

  IconData _getNextStatusActionIcon(TaskStatus status) {
    switch (status) {
      case TaskStatus.assigned:
        return Icons.thumb_up_alt_outlined;
      case TaskStatus.accepted:
        return Icons.navigation_outlined;
      case TaskStatus.travellingToPickup:
        return Icons.place_outlined;
      case TaskStatus.atPickup:
        return Icons.local_shipping_outlined;
      case TaskStatus.inTransit:
        return Icons.flag_outlined;
      case TaskStatus.atDestination:
        return Icons.check_circle_outline;
      case TaskStatus.completed:
      case TaskStatus.cancelled:
        return Icons.done_all;
    }
  }

  Future<void> _handleStatusUpdate(String taskId, TaskStatus newStatus) async {
    if (_isUpdatingStatus) return;
    setState(() => _isUpdatingStatus = true);

    try {
      await widget.taskService.updateTaskStatus(taskId, newStatus);
      await _loadDashboardData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceDark,
            content: Text('Task $taskId updated to ${newStatus.displayName}'),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.statusRed,
            content: Text(e.toString()),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingStatus = false);
      }
    }
  }

  void _showStatusDialogForTask(TransportTask task) {
    showDialog(
      context: context,
      builder: (ctx) => TaskStatusDialog(
        task: task,
        onStatusSelected: (status) => _handleStatusUpdate(task.id, status),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final driver = _driver ?? MockDataService.sampleDriver;
    final currentTask = _activeTasks.isNotEmpty ? _activeTasks.first : null;

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'TERMINAL DRIVER DASHBOARD',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'Component 2: Optimization Dispatch',
              style: TextStyle(color: AppTheme.portCyan, fontSize: 11),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.notifications_outlined),
                if (_unreadNotifications > 0)
                  Positioned(
                    right: -2,
                    top: -2,
                    child: Container(
                      padding: const EdgeInsets.all(3),
                      decoration: const BoxDecoration(
                        color: AppTheme.statusRed,
                        shape: BoxShape.circle,
                      ),
                      constraints: const BoxConstraints(
                        minWidth: 16,
                        minHeight: 16,
                      ),
                      child: Text(
                        '$_unreadNotifications',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
              ],
            ),
            onPressed: () async {
              await Navigator.of(context).pushNamed(AppRoutes.notifications);
              _loadDashboardData();
            },
            tooltip: 'Notifications & Alerts',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboardData,
            tooltip: 'Refresh Dashboard',
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () async {
              await Navigator.of(context).pushNamed('/profile');
              _loadDashboardData();
            },
            tooltip: 'Profile & Settings',
          ),
        ],
      ),
      body: _isLoading
          ? const LoadingIndicator(message: 'Syncing driver dashboard...')
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
              color: AppTheme.portAmber,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Driver & Truck Summary Card
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.borderSubtle),
                      ),
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    driver.name,
                                    style: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'ID: ${driver.id} · Truck: ${_truck.id}',
                                    style: const TextStyle(
                                      color: AppTheme.textSecondary,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                              StatusBadge.fromTruckStatus(_truck.status),
                            ],
                          ),
                          const Divider(height: 20),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  const Icon(
                                    Icons.work_outline,
                                    size: 16,
                                    color: AppTheme.portCyan,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    driver.dutyStatus.displayName,
                                    style: const TextStyle(
                                      color: AppTheme.portCyan,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                              Text(
                                driver.shift,
                                style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Metrics Row
                    Row(
                      children: [
                        Expanded(
                          child: InfoCard(
                            title: 'Active Tasks',
                            value: '${_activeTasks.length}',
                            icon: Icons.assignment_outlined,
                            accentColor: AppTheme.portAmber,
                            onTap: () async {
                              await Navigator.of(context).pushNamed('/tasks');
                              _loadDashboardData();
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: InfoCard(
                            title: 'Done Today',
                            value: '${driver.totalCompletedTasksToday}',
                            icon: Icons.check_circle_outline,
                            accentColor: AppTheme.statusGreen,
                            onTap: () {
                              Navigator.of(context).pushNamed('/history');
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: InfoCard(
                            title: 'Truck Fuel',
                            value: '${_truck.fuelLevelPercentage.toInt()}%',
                            icon: Icons.local_gas_station_outlined,
                            accentColor: AppTheme.portCyan,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),

                    // Section: Current Active Task Spotlight
                    const Text(
                      'CURRENT ACTIVE MISSION',
                      style: TextStyle(
                        color: AppTheme.portAmber,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 8),

                    if (currentTask != null) ...[
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    currentTask.id,
                                    style: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Row(
                                    children: [
                                      StatusBadge.fromPriority(
                                        currentTask.priority,
                                      ),
                                      const SizedBox(width: 6),
                                      StatusBadge.fromTaskStatus(
                                        currentTask.status,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                'Container: ${currentTask.containerId} (${currentTask.containerSize})',
                                style: const TextStyle(
                                  color: AppTheme.portCyan,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const Divider(height: 20),

                              // Route summary
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Icon(
                                    Icons.trip_origin,
                                    color: AppTheme.portAmber,
                                    size: 18,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const Text(
                                          'Pickup',
                                          style: TextStyle(
                                            color: AppTheme.textSecondary,
                                            fontSize: 11,
                                          ),
                                        ),
                                        Text(
                                          currentTask.pickupZone,
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 13,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Icon(
                                    Icons.location_on,
                                    color: AppTheme.statusGreen,
                                    size: 18,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const Text(
                                          'Destination',
                                          style: TextStyle(
                                            color: AppTheme.textSecondary,
                                            fontSize: 11,
                                          ),
                                        ),
                                        Text(
                                          currentTask.destinationZone,
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 13,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 16),

                              // One-Tap Quick Transition Button (Canonical next step)
                              if (currentTask.status.nextStatus != null) ...[
                                ElevatedButton.icon(
                                  onPressed: () => _handleStatusUpdate(
                                    currentTask.id,
                                    currentTask.status.nextStatus!,
                                  ),
                                  icon: Icon(
                                    _getNextStatusActionIcon(
                                        currentTask.status),
                                    color: Colors.black,
                                    size: 20,
                                  ),
                                  label: Text(
                                    _getNextStatusActionLabel(
                                        currentTask.status),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    minimumSize: const Size.fromHeight(46),
                                    backgroundColor: AppTheme.portAmber,
                                  ),
                                ),
                                const SizedBox(height: 10),
                              ],

                              // Secondary Actions Row
                              Row(
                                children: [
                                  Expanded(
                                    child: OutlinedButton.icon(
                                      onPressed: () async {
                                        await Navigator.of(context).pushNamed(
                                          '/task-details',
                                          arguments: currentTask.id,
                                        );
                                        _loadDashboardData();
                                      },
                                      icon: const Icon(
                                        Icons.visibility_outlined,
                                        size: 16,
                                      ),
                                      label: const Text(
                                        'VIEW DETAILS',
                                        style: TextStyle(fontSize: 12),
                                      ),
                                      style: OutlinedButton.styleFrom(
                                        minimumSize: const Size.fromHeight(40),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: OutlinedButton.icon(
                                      onPressed: () =>
                                          _showStatusDialogForTask(currentTask),
                                      icon: const Icon(
                                        Icons.sync_alt,
                                        size: 16,
                                      ),
                                      label: const Text(
                                        'STATUS OPTIONS',
                                        style: TextStyle(fontSize: 12),
                                      ),
                                      style: OutlinedButton.styleFrom(
                                        minimumSize: const Size.fromHeight(40),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ] else ...[
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceDark,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: const Center(
                          child: Column(
                            children: [
                              Icon(
                                Icons.check_circle_outline,
                                color: AppTheme.statusGreen,
                                size: 40,
                              ),
                              SizedBox(height: 8),
                              Text(
                                'No Active Assignments',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Standing by for optimization engine dispatch.',
                                style: TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],

                    const SizedBox(height: 20),

                    // Quick Navigation Hub
                    const Text(
                      'OPERATIONAL SECTIONS',
                      style: TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 8),

                    _buildNavigationTile(
                      title: 'Assigned Transport Tasks',
                      subtitle:
                          '${_activeTasks.length} active assignments awaiting execution',
                      icon: Icons.list_alt,
                      color: AppTheme.portAmber,
                      onTap: () async {
                        await Navigator.of(context).pushNamed('/tasks');
                        _loadDashboardData();
                      },
                    ),
                    const SizedBox(height: 8),
                    _buildNavigationTile(
                      title: 'Task History & Shift Log',
                      subtitle:
                          '${driver.totalCompletedTasksToday} container transfers completed today',
                      icon: Icons.history,
                      color: AppTheme.statusGreen,
                      onTap: () {
                        Navigator.of(context).pushNamed('/history');
                      },
                    ),
                    const SizedBox(height: 8),
                    _buildNavigationTile(
                      title: 'Driver Profile & Connectivity',
                      subtitle:
                          'Duty status, truck specs & backend API configuration',
                      icon: Icons.tune,
                      color: AppTheme.portCyan,
                      onTap: () async {
                        await Navigator.of(context).pushNamed('/profile');
                        _loadDashboardData();
                      },
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildNavigationTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Card(
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(
          title,
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.bold,
            fontSize: 14,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
        ),
        trailing: const Icon(
          Icons.chevron_right,
          color: AppTheme.textSecondary,
        ),
      ),
    );
  }
}
