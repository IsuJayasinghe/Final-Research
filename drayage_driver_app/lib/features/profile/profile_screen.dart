import 'package:flutter/material.dart';

import '../../services/auth_service.dart';
import '../../models/driver.dart';
import '../../app/theme.dart';
import '../../core/config/app_config.dart';

class ProfileScreen extends StatefulWidget {
  final AuthService authService;

  const ProfileScreen({super.key, required this.authService});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Driver? _driver;

  @override
  void initState() {
    super.initState();
    _driver = widget.authService.currentDriver;
  }

  void _changeDutyStatus(DriverDutyStatus newStatus) {
    widget.authService.updateDutyStatus(newStatus);
    setState(() {
      _driver = widget.authService.currentDriver;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Duty status changed to ${newStatus.displayName}'),
        backgroundColor: AppTheme.surfaceDark,
      ),
    );
  }

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text(
          'Confirm Sign Out',
          style: TextStyle(color: AppTheme.textPrimary),
        ),
        content: const Text(
          'Are you sure you want to end your current terminal driver session?',
          style: TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text(
              'Cancel',
              style: TextStyle(color: AppTheme.textSecondary),
            ),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.statusRed,
            ),
            child: const Text(
              'Sign Out',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await widget.authService.logout();
      if (mounted) {
        Navigator.of(context)
            .pushNamedAndRemoveUntil('/login', (route) => false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final driver = _driver ?? widget.authService.currentDriver;

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(title: const Text('Driver Profile & Setup')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Driver Profile Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 36,
                    backgroundColor: AppTheme.cardDark,
                    child: Text(
                      driver != null
                          ? driver.name.substring(0, 2).toUpperCase()
                          : 'DR',
                      style: const TextStyle(
                        color: AppTheme.portAmber,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    driver?.name ?? 'Terminal Driver',
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Driver ID: ${driver?.id ?? "N/A"} · License: ${driver?.licenseNumber ?? "N/A"}',
                    style: const TextStyle(
                      color: AppTheme.portCyan,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Duty Status Toggle Card
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
                  const Text(
                    'DUTY STATUS',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    children: DriverDutyStatus.values.map((status) {
                      final isSelected = driver?.dutyStatus == status;
                      return ChoiceChip(
                        label: Text(status.displayName),
                        selected: isSelected,
                        selectedColor: AppTheme.portAmber,
                        labelStyle: TextStyle(
                          color:
                              isSelected ? Colors.black : AppTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                        onSelected: (val) {
                          if (val) _changeDutyStatus(status);
                        },
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Truck Assignment & Shift
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
                  const Text(
                    'PORT TERMINAL DETAILS',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const Divider(),
                  _buildRow(
                    'Assigned Truck ID',
                    driver?.assignedTruckId ?? 'TRK-025',
                  ),
                  _buildRow('Shift Roster', driver?.shift ?? 'Day Shift'),
                  _buildRow(
                    'Tasks Completed Today',
                    '${driver?.totalCompletedTasksToday ?? 0} missions',
                  ),
                  _buildRow(
                    'Work Contact',
                    driver?.email ?? 'driver@portops.local',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // System & Architecture Information
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
                  const Text(
                    'INTEGRATION & BACKEND SPEC',
                    style: TextStyle(
                      color: AppTheme.portCyan,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const Divider(),
                  _buildRow('App Name', AppConfig.appName),
                  _buildRow('App Version', AppConfig.appVersion),
                  _buildRow(
                    'Research Scope',
                    'Component 2 - Drayage Optimization',
                  ),
                  _buildRow(
                    'Data Source',
                    AppConfig.useMockData
                        ? 'Mock Data Service (Isolated)'
                        : 'FastAPI REST API',
                  ),
                  _buildRow('Target Backend', AppConfig.defaultApiBaseUrl),
                ],
              ),
            ),
            const SizedBox(height: 24),

            OutlinedButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout, color: AppTheme.statusRed),
              label: const Text(
                'SIGN OUT',
                style: TextStyle(color: AppTheme.statusRed),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppTheme.statusRed),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value) {
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
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
