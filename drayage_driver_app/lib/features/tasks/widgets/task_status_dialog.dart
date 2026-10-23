import 'package:flutter/material.dart';

import '../../../models/transport_task.dart';
import '../../../app/theme.dart';
import '../../../widgets/status_badge.dart';

/// Modal dialog allowing drivers to update the task status through permitted transitions.
class TaskStatusDialog extends StatefulWidget {
  final TransportTask task;
  final Function(TaskStatus newStatus) onStatusSelected;

  const TaskStatusDialog({
    super.key,
    required this.task,
    required this.onStatusSelected,
  });

  @override
  State<TaskStatusDialog> createState() => _TaskStatusDialogState();
}

class _TaskStatusDialogState extends State<TaskStatusDialog> {
  TaskStatus? _selectedStatus;

  @override
  void initState() {
    super.initState();
    _selectedStatus = widget.task.status.nextStatus;
  }

  @override
  Widget build(BuildContext context) {
    final allowed = widget.task.status.allowedTransitions;

    return AlertDialog(
      backgroundColor: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Row(
        children: [
          Icon(Icons.sync_alt, color: AppTheme.portAmber),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Update Task Status',
              style: TextStyle(color: AppTheme.textPrimary, fontSize: 18),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Task: ${widget.task.id} (${widget.task.containerId})',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Text(
                  'Current: ',
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                ),
                StatusBadge.fromTaskStatus(widget.task.status),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Select Next Status:',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 8),
            if (allowed.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8.0),
                child: Text(
                  'This task has reached a terminal status (Completed/Cancelled). No further transitions allowed.',
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                ),
              )
            else
              ...allowed.map((status) {
                final isRecommended = status == widget.task.status.nextStatus;
                final isSelected = _selectedStatus == status;
                return Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(8),
                    onTap: () {
                      setState(() {
                        _selectedStatus = status;
                      });
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 12),
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppTheme.portAmber.withValues(alpha: 0.15)
                            : AppTheme.cardDark,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isSelected
                              ? AppTheme.portAmber
                              : AppTheme.borderSubtle,
                          width: isSelected ? 1.5 : 1.0,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            isSelected
                                ? Icons.radio_button_checked
                                : Icons.radio_button_unchecked,
                            color: isSelected
                                ? AppTheme.portAmber
                                : AppTheme.textSecondary,
                            size: 20,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              status.displayName,
                              style: TextStyle(
                                color: isSelected
                                    ? AppTheme.portAmber
                                    : AppTheme.textPrimary,
                                fontWeight: isSelected
                                    ? FontWeight.bold
                                    : FontWeight.w600,
                                fontSize: 14,
                              ),
                            ),
                          ),
                          if (isRecommended)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: AppTheme.portCyan.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'NEXT',
                                style: TextStyle(
                                  color: AppTheme.portCyan,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text(
            'Cancel',
            style: TextStyle(color: AppTheme.textSecondary),
          ),
        ),
        ElevatedButton(
          onPressed: (_selectedStatus == null || allowed.isEmpty)
              ? null
              : () {
                  Navigator.of(context).pop();
                  widget.onStatusSelected(_selectedStatus!);
                },
          style: ElevatedButton.styleFrom(
            minimumSize: const Size(110, 42),
            backgroundColor: AppTheme.portAmber,
          ),
          child: const Text('Confirm'),
        ),
      ],
    );
  }
}
