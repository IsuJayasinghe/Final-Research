import 'package:flutter/material.dart';

import '../../models/transport_task.dart';
import '../../services/task_service.dart';
import '../../app/theme.dart';
import '../../core/utils/date_formatter.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/error_message.dart';

class TaskHistoryScreen extends StatefulWidget {
  final TaskService taskService;

  const TaskHistoryScreen({super.key, required this.taskService});

  @override
  State<TaskHistoryScreen> createState() => _TaskHistoryScreenState();
}

class _TaskHistoryScreenState extends State<TaskHistoryScreen> {
  List<TransportTask> _historyTasks = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final tasks = await widget.taskService.getCompletedTasks();
      setState(() {
        _historyTasks = tasks;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: const Text('Completed Task History'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadHistory),
        ],
      ),
      body: _isLoading
          ? const LoadingIndicator(message: 'Loading shift history...')
          : _errorMessage != null
              ? ErrorMessage(message: _errorMessage!, onRetry: _loadHistory)
              : _historyTasks.isEmpty
                  ? const Center(
                      child: Text(
                        'No completed tasks recorded for this shift.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _historyTasks.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final task = _historyTasks[index];
                        return Card(
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
                                      task.id,
                                      style: const TextStyle(
                                        color: AppTheme.textPrimary,
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    StatusBadge.fromTaskStatus(task.status),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Container: ${task.containerId} (${task.containerSize})',
                                  style: const TextStyle(
                                    color: AppTheme.portCyan,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Row(
                                  children: [
                                    const Icon(
                                      Icons.pin_drop,
                                      size: 14,
                                      color: AppTheme.portAmber,
                                    ),
                                    const SizedBox(width: 4),
                                    Expanded(
                                      child: Text(
                                        'From: ${task.pickupZone}',
                                        style: const TextStyle(
                                          color: AppTheme.textSecondary,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(
                                      Icons.flag,
                                      size: 14,
                                      color: AppTheme.statusGreen,
                                    ),
                                    const SizedBox(width: 4),
                                    Expanded(
                                      child: Text(
                                        'To: ${task.destinationZone}',
                                        style: const TextStyle(
                                          color: AppTheme.textSecondary,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const Divider(),
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      task.completedAt != null
                                          ? 'Completed: ${DateFormatter.formatTime(task.completedAt!)}'
                                          : 'Completed',
                                      style: const TextStyle(
                                        color: AppTheme.statusGreen,
                                        fontSize: 12,
                                      ),
                                    ),
                                    Text(
                                      '${task.estimatedDistanceKm} km',
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
