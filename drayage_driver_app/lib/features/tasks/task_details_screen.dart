import 'package:flutter/material.dart';

import '../../models/transport_task.dart';
import '../../services/task_service.dart';
import '../../app/theme.dart';
import '../../core/utils/date_formatter.dart';
import '../../widgets/status_badge.dart';
import 'widgets/task_status_dialog.dart';

class TaskDetailsScreen extends StatefulWidget {
  final String taskId;
  final TaskService taskService;

  const TaskDetailsScreen({
    super.key,
    required this.taskId,
    required this.taskService,
  });

  @override
  State<TaskDetailsScreen> createState() => _TaskDetailsScreenState();
}

class _TaskDetailsScreenState extends State<TaskDetailsScreen> {
  TransportTask? _task;
  bool _isLoading = true;
  bool _isUpdatingStatus = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadTask();
  }

  Future<void> _loadTask() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final task = await widget.taskService.getTaskById(widget.taskId);
      setState(() {
        _task = task;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _handleStatusUpdate(TaskStatus newStatus) async {
    if (_task == null || _isUpdatingStatus) return;
    setState(() => _isUpdatingStatus = true);

    try {
      final updated = await widget.taskService.updateTaskStatus(
        _task!.id,
        newStatus,
      );
      setState(() {
        _task = updated;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceDark,
            content: Row(
              children: [
                const Icon(Icons.check_circle, color: AppTheme.statusGreen),
                const SizedBox(width: 8),
                Text('Task status updated to ${newStatus.displayName}'),
              ],
            ),
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

  void _showStatusDialog() {
    if (_task == null) return;
    showDialog(
      context: context,
      builder: (ctx) =>
          TaskStatusDialog(task: _task!, onStatusSelected: _handleStatusUpdate),
    );
  }

  String _getNextStatusActionLabel(TaskStatus status) {
    switch (status) {
      case TaskStatus.assigned:
        return 'ACCEPT MISSION';
      case TaskStatus.accepted:
        return 'START TRIP TO PICKUP';
      case TaskStatus.travellingToPickup:
        return 'CONFIRM ARRIVAL AT PICKUP';
      case TaskStatus.atPickup:
        return 'CONFIRM LOAD & START TRANSIT';
      case TaskStatus.inTransit:
        return 'CONFIRM ARRIVAL AT DESTINATION';
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

  Widget _buildProgressStepper(TaskStatus current) {
    final stages = [
      {'status': TaskStatus.assigned, 'label': 'Assigned'},
      {'status': TaskStatus.accepted, 'label': 'Accepted'},
      {'status': TaskStatus.travellingToPickup, 'label': 'To Pickup'},
      {'status': TaskStatus.atPickup, 'label': 'At Pickup'},
      {'status': TaskStatus.inTransit, 'label': 'In Transit'},
      {'status': TaskStatus.atDestination, 'label': 'At Dest'},
      {'status': TaskStatus.completed, 'label': 'Done'},
    ];

    final currentIndex = stages.indexWhere((s) => s['status'] == current);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'OPERATION LIFECYCLE PROGRESS',
            style: TextStyle(
              color: AppTheme.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List.generate(stages.length, (idx) {
                final isReached = currentIndex >= idx;
                final isCurrent = currentIndex == idx;
                final stage = stages[idx];

                return Row(
                  children: [
                    Column(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isCurrent
                                ? AppTheme.portAmber
                                : (isReached
                                    ? AppTheme.portCyan
                                    : AppTheme.cardDark),
                            border: Border.all(
                              color: isCurrent
                                  ? Colors.white
                                  : AppTheme.borderSubtle,
                              width: isCurrent ? 2 : 1,
                            ),
                          ),
                          child: Icon(
                            isReached ? Icons.check : Icons.circle,
                            size: 14,
                            color: isReached
                                ? Colors.black
                                : AppTheme.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          stage['label'] as String,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight:
                                isCurrent ? FontWeight.bold : FontWeight.normal,
                            color: isCurrent
                                ? AppTheme.portAmber
                                : (isReached
                                    ? AppTheme.textPrimary
                                    : AppTheme.textSecondary),
                          ),
                        ),
                      ],
                    ),
                    if (idx < stages.length - 1)
                      Container(
                        width: 24,
                        height: 2,
                        color: currentIndex > idx
                            ? AppTheme.portCyan
                            : AppTheme.borderSubtle,
                        margin: const EdgeInsets.symmetric(
                          horizontal: 4,
                          vertical: 14,
                        ),
                      ),
                  ],
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Task Details')),
        body: const Center(
          child: CircularProgressIndicator(color: AppTheme.portAmber),
        ),
      );
    }

    if (_errorMessage != null || _task == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Task Details')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _errorMessage ?? 'Task not found',
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _loadTask, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final task = _task!;

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text('Task ${task.id}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadTask,
            tooltip: 'Refresh Task',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header card with ID, priority, status
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        task.id,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      StatusBadge.fromPriority(task.priority),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Text(
                        'Status: ',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                      StatusBadge.fromTaskStatus(task.status),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Assigned: ${DateFormatter.formatDateTime(task.assignedAt)}',
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                  if (task.completedAt != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Completed: ${DateFormatter.formatDateTime(task.completedAt!)}',
                      style: const TextStyle(
                        color: AppTheme.statusGreen,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Progress Stepper
            _buildProgressStepper(task.status),
            const SizedBox(height: 14),

            // Container info card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.inventory_2_outlined,
                        color: AppTheme.portAmber,
                        size: 20,
                      ),
                      SizedBox(width: 8),
                      Text(
                        'CONTAINER SPECIFICATIONS',
                        style: TextStyle(
                          color: AppTheme.portAmber,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const Divider(),
                  _buildDetailRow(
                    'Container Number',
                    task.containerId,
                    isBold: true,
                  ),
                  _buildDetailRow('Size Specification', task.containerSize),
                  _buildDetailRow('Cargo Type', task.containerType),
                  _buildDetailRow(
                    'Assigned Truck',
                    task.assignedTruckId ?? 'Not Set',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Locations card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.alt_route, color: AppTheme.portCyan, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'ORIGIN & DESTINATION',
                        style: TextStyle(
                          color: AppTheme.portCyan,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const Divider(),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.trip_origin,
                        color: AppTheme.portAmber,
                        size: 18,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Pickup Zone',
                              style: TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              task.pickupZone,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const Padding(
                    padding: EdgeInsets.only(left: 8.0),
                    child: SizedBox(
                      height: 24,
                      child: VerticalDivider(
                        color: AppTheme.borderSubtle,
                        thickness: 2,
                      ),
                    ),
                  ),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.location_on,
                        color: AppTheme.statusGreen,
                        size: 18,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Destination Zone',
                              style: TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              task.destinationZone,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Est. Distance: ${task.estimatedDistanceKm} km',
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      Text(
                        'Est. Time: ${task.estimatedTimeMinutes} mins',
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Instructions card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.info_outline,
                        color: AppTheme.textSecondary,
                        size: 18,
                      ),
                      SizedBox(width: 8),
                      Text(
                        'DISPATCH INSTRUCTIONS',
                        style: TextStyle(
                          color: AppTheme.textSecondary,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    task.instructions.isNotEmpty
                        ? task.instructions
                        : 'No special instructions provided.',
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 14,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Action Buttons
            if (task.status.nextStatus != null) ...[
              ElevatedButton.icon(
                onPressed: () => _handleStatusUpdate(task.status.nextStatus!),
                icon: Icon(
                  _getNextStatusActionIcon(task.status),
                  color: Colors.black,
                  size: 20,
                ),
                label: Text(
                  _getNextStatusActionLabel(task.status),
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                  backgroundColor: AppTheme.portAmber,
                ),
              ),
              const SizedBox(height: 10),
            ],

            OutlinedButton.icon(
              onPressed: _showStatusDialog,
              icon: const Icon(Icons.sync_alt),
              label: const Text('ALL STATUS OPTIONS...'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(44),
              ),
            ),
            const SizedBox(height: 10),

            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).pushNamed('/route', arguments: task);
              },
              icon: const Icon(Icons.map_outlined),
              label: const Text('VIEW RECOMMENDED ROUTE'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(44),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
          ),
          Text(
            value,
            style: TextStyle(
              color: AppTheme.textPrimary,
              fontWeight: isBold ? FontWeight.bold : FontWeight.w500,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
