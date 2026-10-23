/// Custom exceptions for handling application and network errors gracefully.
class AppException implements Exception {
  final String message;
  final String? code;

  const AppException(this.message, {this.code});

  @override
  String toString() => code != null ? '[$code] $message' : message;
}

class NetworkException extends AppException {
  const NetworkException([
    super.message =
        'Network connection interrupted. Please verify connectivity.',
  ]) : super(code: 'NETWORK_ERR');
}

class AuthenticationException extends AppException {
  const AuthenticationException([
    super.message = 'Invalid driver credentials or expired session.',
  ]) : super(code: 'AUTH_ERR');
}

class TaskTransitionException extends AppException {
  const TaskTransitionException([
    super.message = 'Invalid status transition for this transport task.',
  ]) : super(code: 'INVALID_TRANSITION');
}

class LocationUnavailableException extends AppException {
  const LocationUnavailableException([
    super.message = 'GPS location unavailable or permission denied.',
  ]) : super(code: 'GPS_ERR');
}
