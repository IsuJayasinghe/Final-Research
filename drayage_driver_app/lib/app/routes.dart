import 'package:flutter/material.dart';

import '../features/auth/login_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/tasks/assigned_tasks_screen.dart';
import '../features/tasks/task_details_screen.dart';
import '../features/navigation/route_screen.dart';
import '../features/history/task_history_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/profile/profile_screen.dart';
import '../models/transport_task.dart';
import '../services/auth_service.dart';
import '../services/task_service.dart';
import '../services/notification_service.dart';

/// Centralized application routes for the Driver Mobile App.
class AppRoutes {
  static const String login = '/login';
  static const String dashboard = '/dashboard';
  static const String tasks = '/tasks';
  static const String taskDetails = '/task-details';
  static const String route = '/route';
  static const String history = '/history';
  static const String profile = '/profile';
  static const String notifications = '/notifications';

  static Route<dynamic> onGenerateRoute(
    RouteSettings settings, {
    required AuthService authService,
    required TaskService taskService,
    required NotificationService notificationService,
  }) {
    switch (settings.name) {
      case login:
        return MaterialPageRoute(
          builder: (_) => LoginScreen(authService: authService),
          settings: settings,
        );

      case dashboard:
        return MaterialPageRoute(
          builder: (_) => DashboardScreen(
            authService: authService,
            taskService: taskService,
            notificationService: notificationService,
          ),
          settings: settings,
        );

      case tasks:
        return MaterialPageRoute(
          builder: (_) => AssignedTasksScreen(taskService: taskService),
          settings: settings,
        );

      case taskDetails:
        final taskId = settings.arguments as String;
        return MaterialPageRoute(
          builder: (_) =>
              TaskDetailsScreen(taskId: taskId, taskService: taskService),
          settings: settings,
        );

      case route:
        final task = settings.arguments as TransportTask;
        return MaterialPageRoute(
          builder: (_) => RouteScreen(task: task),
          settings: settings,
        );

      case history:
        return MaterialPageRoute(
          builder: (_) => TaskHistoryScreen(taskService: taskService),
          settings: settings,
        );

      case profile:
        return MaterialPageRoute(
          builder: (_) => ProfileScreen(authService: authService),
          settings: settings,
        );

      case notifications:
        return MaterialPageRoute(
          builder: (_) =>
              NotificationsScreen(notificationService: notificationService),
          settings: settings,
        );

      default:
        return MaterialPageRoute(
          builder: (_) => LoginScreen(authService: authService),
          settings: settings,
        );
    }
  }
}
