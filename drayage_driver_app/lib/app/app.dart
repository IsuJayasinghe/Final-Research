import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import '../services/task_service.dart';
import '../services/notification_service.dart';
import 'routes.dart';
import 'theme.dart';
import '../core/config/app_config.dart';

/// Root application widget for Port Drayage Driver (Component 2).
class DrayageDriverApp extends StatefulWidget {
  final AuthService authService;
  final TaskService taskService;
  final NotificationService? notificationService;

  const DrayageDriverApp({
    super.key,
    required this.authService,
    required this.taskService,
    this.notificationService,
  });

  @override
  State<DrayageDriverApp> createState() => _DrayageDriverAppState();
}

class _DrayageDriverAppState extends State<DrayageDriverApp> {
  late final NotificationService _notificationService;

  @override
  void initState() {
    super.initState();
    _notificationService = widget.notificationService ?? NotificationService();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      initialRoute: widget.authService.isAuthenticated
          ? AppRoutes.dashboard
          : AppRoutes.login,
      onGenerateRoute: (settings) => AppRoutes.onGenerateRoute(
        settings,
        authService: widget.authService,
        taskService: widget.taskService,
        notificationService: _notificationService,
      ),
    );
  }
}
