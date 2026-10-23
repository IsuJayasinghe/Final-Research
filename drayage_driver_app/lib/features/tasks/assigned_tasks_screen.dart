import 'package:flutter/material.dart';

import '../../models/transport_task.dart';
import '../../services/task_service.dart';
import '../../app/theme.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/error_message.dart';

class AssignedTasksScreen extends StatefulWidget {
  final TaskService taskService;

  const AssignedTasksScreen({super.key, required this.taskService});

  @override
  State<AssignedTasksScreen> createState() => _AssignedTasksScreenState();
}

class _AssignedTasksScreenState extends State<AssignedTasksScreen> {
  List<TransportTask> _tasks = [];
  bool _isLoading = true;
  String? _errorMessage;
  int _selectedFilterIndex = 0; // 0: All Active, 1: High/Urgent

  @override
  void initState() {
    super.initState();
    _loadTasks();
  }

  Future<void> _loadTasks() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final tasks = await widget.taskService.getActiveTasks();
      setState(() {
        _tasks = tasks;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  List<TransportTask> get _filteredTasks {
    if (_selectedFilterIndex == 1) {
      return _tasks
          .where(
            (t) =>
                t.priority == TaskPriority.high ||
                t.priority == TaskPriority.urgent,
          )
          .toList();
    }
    return _tasks;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: const Text('Assigned Transport Tasks'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadTasks,
            tooltip: 'Refresh assignments',
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter Chips
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppTheme.surfaceDark,
            child: Row(
              children: [
                ChoiceChip(
                  label: Text('All Active (${_tasks.length})'),
                  selected: _selectedFilterIndex == 0,
                  selectedColor: AppTheme.portAmber,
                  labelStyle: TextStyle(
                    color: _selectedFilterIndex == 0
                        ? Colors.black
                        : AppTheme.textPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                  onSelected: (val) {
                    if (val) setState(() => _selectedFilterIndex = 0);
                  },
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: const Text('Priority / Urgent'),
                  selected: _selectedFilterIndex == 1,
                  selectedColor: AppTheme.portAmber,
                  labelStyle: TextStyle(
                    color: _selectedFilterIndex == 1
                        ? Colors.black
                        : AppTheme.textPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                  onSelected: (val) {
                    if (val) setState(() => _selectedFilterIndex = 1);
                  },
                ),
              ],
            ),
          ),

          // Main list
          Expanded(
            child: _isLoading
                ? const LoadingIndicator(
                    message:
                        'Retrieving assigned tasks from optimization engine...',
                  )
                : _errorMessage != null
                    ? ErrorMessage(message: _errorMessage!, onRetry: _loadTasks)
                    : _filteredTasks.isEmpty
                        ? const Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.task_alt,
                                  color: AppTheme.textSecondary,
                                  size: 48,
                                ),
                                SizedBox(height: 12),
                                Text(
                                  'No active tasks assigned to your truck.',
                                  style: TextStyle(
                                    color: AppTheme.textSecondary,
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: _loadTasks,
                            color: AppTheme.portAmber,
                            child: ListView.separated(
                              padding: const EdgeInsets.all(16),
                              itemCount: _filteredTasks.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 12),
                              itemBuilder: (context, index) {
                                final task = _filteredTasks[index];
                                return _buildTaskCard(task);
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildTaskCard(TransportTask task) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () async {
          await Navigator.of(context)
              .pushNamed('/task-details', arguments: task.id);
          _loadTasks();
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Row 1: Task ID & Priority & Status
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.assignment,
                        color: AppTheme.portAmber,
                        size: 20,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        task.id,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      StatusBadge.fromPriority(task.priority),
                      const SizedBox(width: 6),
                      StatusBadge.fromTaskStatus(task.status),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Row 2: Container ID & Specs
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppTheme.cardDark,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Container: ${task.containerId}',
                      style: const TextStyle(
                        color: AppTheme.portCyan,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      '${task.containerSize} · ${task.containerType}',
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              // Row 3: Pickup & Destination
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.trip_origin,
                    color: AppTheme.portAmber,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'From: ${task.pickupZone}',
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 13,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.location_on,
                    color: AppTheme.statusGreen,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'To: ${task.destinationZone}',
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 13,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Row 4: Distance & Arrow
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Est. ${task.estimatedDistanceKm} km · ${task.estimatedTimeMinutes} mins',
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                  const Row(
                    children: [
                      Text(
                        'Details',
                        style: TextStyle(
                          color: AppTheme.portAmber,
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Icon(
                        Icons.chevron_right,
                        color: AppTheme.portAmber,
                        size: 18,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
