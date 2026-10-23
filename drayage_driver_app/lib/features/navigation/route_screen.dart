import 'dart:async';
import 'package:flutter/material.dart';

import '../../models/transport_task.dart';
import '../../app/theme.dart';

class RouteScreen extends StatefulWidget {
  final TransportTask task;

  const RouteScreen({super.key, required this.task});

  @override
  State<RouteScreen> createState() => _RouteScreenState();
}

class _RouteScreenState extends State<RouteScreen> {
  bool _isSimulating = false;
  Timer? _telemetryTimer;
  int _activeWaypointIndex = 1;
  double _currentSpeedKmh = 18.5;
  double _lat = 6.9428;
  double _lng = 79.8452;
  double _heading = 84.0;

  @override
  void dispose() {
    _telemetryTimer?.cancel();
    super.dispose();
  }

  void _toggleSimulation() {
    setState(() {
      _isSimulating = !_isSimulating;
    });

    if (_isSimulating) {
      _telemetryTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }

        setState(() {
          // Incrementally advance simulated telemetry
          _lat += 0.0003;
          _lng += 0.0002;
          _currentSpeedKmh = 16.0 + ((_currentSpeedKmh * 7 + 13) % 9);
          _heading = (_heading + 5) % 360;

          if (_activeWaypointIndex < 3) {
            _activeWaypointIndex++;
          }
        });
      });
    } else {
      _telemetryTimer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text('Route: ${task.id}'),
        actions: [
          IconButton(
            icon: Icon(
              _isSimulating
                  ? Icons.pause_circle_filled
                  : Icons.play_circle_outline,
              color: _isSimulating ? AppTheme.portAmber : AppTheme.portCyan,
            ),
            tooltip:
                _isSimulating ? 'Pause GPS Simulation' : 'Start GPS Simulation',
            onPressed: _toggleSimulation,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Optimization Engine Notice Banner
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.portCyan.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: AppTheme.portCyan.withValues(alpha: 0.4),
                ),
              ),
              child: const Row(
                children: [
                  Icon(Icons.alt_route, color: AppTheme.portCyan, size: 24),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Route calculated by Component 2 Optimization Engine based on real-time port congestion and gantry crane availability.',
                      style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 12,
                        height: 1.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Live GPS & Truck Telemetry Card
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _isSimulating
                      ? AppTheme.portAmber
                      : AppTheme.borderSubtle,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.gps_fixed,
                            size: 16,
                            color: _isSimulating
                                ? AppTheme.statusGreen
                                : AppTheme.portCyan,
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'LIVE TRUCK TELEMETRY',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: (_isSimulating
                                  ? AppTheme.statusGreen
                                  : AppTheme.portCyan)
                              .withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          _isSimulating ? 'TRANSMITTING' : 'IDLE / MOCK',
                          style: TextStyle(
                            color: _isSimulating
                                ? AppTheme.statusGreen
                                : AppTheme.portCyan,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: _buildTelemetryStat(
                          label: 'Coordinates',
                          value:
                              '${_lat.toStringAsFixed(4)}° N, ${_lng.toStringAsFixed(4)}° E',
                        ),
                      ),
                      Expanded(
                        child: _buildTelemetryStat(
                          label: 'Speed',
                          value: '${_currentSpeedKmh.toStringAsFixed(1)} km/h',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildTelemetryStat(
                          label: 'Heading',
                          value: '${_heading.toInt()}° ENE',
                        ),
                      ),
                      Expanded(
                        child: _buildTelemetryStat(
                          label: 'GNSS Accuracy',
                          value: 'RTK Fixed (±0.3m)',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Map Placeholder Graphic
            Container(
              height: 200,
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Stack(
                children: [
                  Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.map_outlined,
                          size: 56,
                          color: AppTheme.portAmber.withValues(alpha: 0.4),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'TERMINAL VECTOR ROUTE MAP',
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.0,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${task.pickupZone}  ➔  ${task.destinationZone}',
                          style: const TextStyle(
                            color: AppTheme.portCyan,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Positioned(
                    top: 10,
                    right: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.7),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.timer_outlined,
                              size: 14, color: AppTheme.portAmber),
                          const SizedBox(width: 4),
                          Text(
                            '${task.estimatedDistanceKm} km · ~${task.estimatedTimeMinutes} min',
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Waypoints & Navigation checkpoints
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
                    'OPTIMAL WAYPOINT SEQUENCE',
                    style: TextStyle(
                      color: AppTheme.portAmber,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const Divider(),
                  _buildWaypoint(
                    step: '1',
                    title: 'Current Truck Position',
                    subtitle: 'Proceed to Terminal Perimeter Arterial',
                    icon: Icons.my_location,
                    color: AppTheme.portAmber,
                    isPassed: _activeWaypointIndex >= 0,
                  ),
                  _buildWaypoint(
                    step: '2',
                    title: 'Pickup Location',
                    subtitle: task.pickupZone,
                    icon: Icons.trip_origin,
                    color: AppTheme.portCyan,
                    isPassed: _activeWaypointIndex >= 1,
                  ),
                  _buildWaypoint(
                    step: '3',
                    title: 'Internal Port Corridor',
                    subtitle: 'Via Central Avenue - Max 25 km/h speed zone',
                    icon: Icons.navigation_outlined,
                    color: AppTheme.textSecondary,
                    isPassed: _activeWaypointIndex >= 2,
                  ),
                  _buildWaypoint(
                    step: '4',
                    title: 'Destination Drop-off',
                    subtitle: task.destinationZone,
                    icon: Icons.flag,
                    color: AppTheme.statusGreen,
                    isPassed: _activeWaypointIndex >= 3,
                    isLast: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            ElevatedButton.icon(
              onPressed: () {
                Navigator.of(context).pop();
              },
              icon: const Icon(Icons.arrow_back),
              label: const Text('BACK TO TASK DETAILS'),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size.fromHeight(46),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTelemetryStat({required String label, required String value}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildWaypoint({
    required String step,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    bool isPassed = false,
    bool isLast = false,
  }) {
    final activeColor = isPassed ? color : AppTheme.textSecondary;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: activeColor.withValues(alpha: 0.15),
                border: Border.all(color: activeColor, width: 1.5),
              ),
              child: Icon(icon, color: activeColor, size: 14),
            ),
            if (!isLast)
              Container(
                width: 2,
                height: 36,
                color: isPassed ? color : AppTheme.borderSubtle,
              ),
          ],
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color:
                      isPassed ? AppTheme.textPrimary : AppTheme.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ],
    );
  }
}
