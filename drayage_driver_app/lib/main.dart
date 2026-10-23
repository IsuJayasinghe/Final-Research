import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app/app.dart';
import 'core/network/api_client.dart';
import 'services/auth_service.dart';
import 'services/task_service.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set system UI overlay style for dark terminal industrial theme
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: Color(0xFF0F172A),
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  // Initialize shared REST API Client
  final apiClient = ApiClient();

  // Initialize core services sharing the authenticated API client
  final authService = AuthService(apiClient: apiClient);
  final taskService = TaskService(apiClient: apiClient);
  final notificationService = NotificationService();

  runApp(
    DrayageDriverApp(
      authService: authService,
      taskService: taskService,
      notificationService: notificationService,
    ),
  );
}
