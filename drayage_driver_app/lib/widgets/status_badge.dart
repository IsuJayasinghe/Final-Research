import 'package:flutter/material.dart';

import '../models/transport_task.dart';
import '../models/truck.dart';
import '../app/theme.dart';

/// Reusable high-visibility status badge for tasks, trucks, and priorities.
class StatusBadge extends StatelessWidget {
  final String label;
  final Color backgroundColor;
  final Color textColor;
  final IconData? icon;

  const StatusBadge({
    super.key,
    required this.label,
    required this.backgroundColor,
    this.textColor = Colors.white,
    this.icon,
  });

  factory StatusBadge.fromTaskStatus(TaskStatus status) {
    Color bg;
    IconData ic;

    switch (status) {
      case TaskStatus.assigned:
        bg = const Color(0xFF3B82F6); // Blue
        ic = Icons.assignment_outlined;
        break;
      case TaskStatus.accepted:
        bg = const Color(0xFF8B5CF6); // Purple
        ic = Icons.thumb_up_alt_outlined;
        break;
      case TaskStatus.travellingToPickup:
        bg = const Color(0xFFF59E0B); // Amber
        ic = Icons.navigation_outlined;
        break;
      case TaskStatus.atPickup:
        bg = const Color(0xFFD97706); // Dark Amber
        ic = Icons.pin_drop_outlined;
        break;
      case TaskStatus.inTransit:
        bg = const Color(0xFF06B6D4); // Cyan
        ic = Icons.local_shipping_outlined;
        break;
      case TaskStatus.atDestination:
        bg = const Color(0xFF0D9488); // Teal
        ic = Icons.flag_outlined;
        break;
      case TaskStatus.completed:
        bg = AppTheme.statusGreen;
        ic = Icons.check_circle_outline;
        break;
      case TaskStatus.cancelled:
        bg = AppTheme.statusRed;
        ic = Icons.cancel_outlined;
        break;
    }

    return StatusBadge(
      label: status.displayName,
      backgroundColor: bg,
      icon: ic,
    );
  }

  factory StatusBadge.fromTruckStatus(TruckStatus status) {
    Color bg;
    IconData ic;

    switch (status) {
      case TruckStatus.available:
        bg = AppTheme.statusGreen;
        ic = Icons.check_circle;
        break;
      case TruckStatus.assigned:
        bg = const Color(0xFF3B82F6);
        ic = Icons.assignment_turned_in;
        break;
      case TruckStatus.travellingToPickup:
      case TruckStatus.atPickup:
      case TruckStatus.inTransit:
      case TruckStatus.atDestination:
        bg = AppTheme.portAmber;
        ic = Icons.local_shipping;
        break;
      case TruckStatus.completed:
        bg = AppTheme.statusGreen;
        ic = Icons.done_all;
        break;
      case TruckStatus.unavailable:
        bg = AppTheme.statusRed;
        ic = Icons.block;
        break;
    }

    return StatusBadge(
      label: status.displayName,
      backgroundColor: bg,
      icon: ic,
    );
  }

  factory StatusBadge.fromPriority(TaskPriority priority) {
    Color bg;
    IconData ic;

    switch (priority) {
      case TaskPriority.low:
        bg = const Color(0xFF64748B);
        ic = Icons.arrow_downward;
        break;
      case TaskPriority.normal:
        bg = const Color(0xFF0284C7);
        ic = Icons.remove;
        break;
      case TaskPriority.high:
        bg = const Color(0xFFEA580C);
        ic = Icons.arrow_upward;
        break;
      case TaskPriority.urgent:
        bg = AppTheme.statusRed;
        ic = Icons.priority_high;
        break;
    }

    return StatusBadge(
      label: priority.displayName,
      backgroundColor: bg,
      icon: ic,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: backgroundColor.withValues(alpha: 0.8),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: backgroundColor),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: backgroundColor,
              fontSize: 12,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}
