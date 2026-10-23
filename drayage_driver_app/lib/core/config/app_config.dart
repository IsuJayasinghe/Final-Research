/// Application Configuration for Component 2: Drayage Driver Mobile App
class AppConfig {
  static const String appName = 'Port Drayage Driver';
  static const String appVersion = '1.0.0';
  static const String componentName =
      'Component 2 - Intelligent Drayage Truck Optimization';

  /// Base URL for the shared Python FastAPI Backend
  /// For physical phone on same Wi-Fi, use your PC's Wi-Fi IP: 10.178.64.163
  /// For Android emulator, use: 10.0.2.2
  static const String defaultApiBaseUrl = 'http://10.178.64.163:8000/api/v1';

  /// Toggle mock data mode for offline development and initial UI testing
  static const bool useMockData = false;

  /// Default polling interval in seconds for task updates
  static const int taskPollingIntervalSeconds = 15;

  /// Default GPS location update interval in seconds
  static const int locationUpdateIntervalSeconds = 10;
}
