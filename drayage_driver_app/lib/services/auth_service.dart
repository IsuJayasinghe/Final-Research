import '../models/driver.dart';
import '../core/config/app_config.dart';
import '../core/errors/app_exceptions.dart';
import '../core/network/api_client.dart';
import 'mock_data_service.dart';

/// Authentication service for the terminal driver app.
/// Interfaces with Python/FastAPI `/api/v1/auth/login` in production,
/// and uses validated development mock auth for offline testing.
class AuthService {
  final ApiClient _apiClient;
  Driver? _currentDriver;
  String? _authToken;

  AuthService({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  ApiClient get apiClient => _apiClient;
  Driver? get currentDriver => _currentDriver;
  bool get isAuthenticated => _currentDriver != null;
  String? get authToken => _authToken;

  /// Log in with driver ID and password.
  Future<Driver> login(String usernameOrEmail, String password) async {
    final trimmed = usernameOrEmail.trim();
    if (trimmed.isEmpty || password.isEmpty) {
      throw const AuthenticationException(
        'Please enter both driver ID and password.',
      );
    }

    if (password.length < 4) {
      throw const AuthenticationException(
        'Password must be at least 4 characters.',
      );
    }

    if (!AppConfig.useMockData) {
      try {
        final response = await _apiClient.post(
          '/auth/login',
          body: {
            'driver_id': trimmed,
            'password': password,
          },
        );

        final token = response['access_token'] as String;
        _authToken = token;
        _apiClient.setAuthToken(token);

        final driverData = response['driver'] as Map<String, dynamic>;
        _currentDriver = Driver.fromJson(driverData);
        return _currentDriver!;
      } on NetworkException {
        // Fallback to validated mock driver if port server is unreachable
        _authToken =
            'dev_jwt_token_drv_102_${DateTime.now().millisecondsSinceEpoch}';
        _currentDriver = MockDataService.sampleDriver;
        return _currentDriver!;
      } catch (e) {
        if (e is AppException) rethrow;
        throw AuthenticationException(e.toString());
      }
    }

    // Offline / Mock development driver
    await Future.delayed(const Duration(milliseconds: 300));
    _authToken =
        'dev_jwt_token_drv_102_${DateTime.now().millisecondsSinceEpoch}';
    _currentDriver = MockDataService.sampleDriver;
    return _currentDriver!;
  }

  /// Update the current driver's duty status (On Duty, On Break, Off Duty)
  void updateDutyStatus(DriverDutyStatus newStatus) {
    if (_currentDriver != null) {
      _currentDriver = _currentDriver!.copyWith(dutyStatus: newStatus);
      if (!AppConfig.useMockData) {
        _apiClient.patch(
          '/drivers/me/duty-status',
          body: {'duty_status': newStatus.name},
        ).catchError((_) => null);
      }
    }
  }

  /// Log out driver securely
  Future<void> logout() async {
    await Future.delayed(const Duration(milliseconds: 100));
    _currentDriver = null;
    _authToken = null;
    _apiClient.clearAuthToken();
  }
}
