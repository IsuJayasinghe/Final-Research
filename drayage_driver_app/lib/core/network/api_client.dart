import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../config/app_config.dart';
import '../errors/app_exceptions.dart';

/// Clean REST API Client for communicating with Component 2 FastAPI backend.
class ApiClient {
  final String baseUrl;
  final Duration timeout;
  String? _authToken;
  final HttpClient _httpClient;

  ApiClient({
    String? baseUrl,
    Duration? timeout,
    HttpClient? httpClient,
  })  : baseUrl = baseUrl ?? AppConfig.defaultApiBaseUrl,
        timeout = timeout ?? const Duration(seconds: 15),
        _httpClient = httpClient ?? HttpClient();

  /// Set the authenticated driver's JWT or Bearer session token
  void setAuthToken(String token) {
    _authToken = token;
  }

  /// Clears the authentication token on driver logout
  void clearAuthToken() {
    _authToken = null;
  }

  bool get isAuthenticated => _authToken != null && _authToken!.isNotEmpty;

  /// Performs HTTP GET request
  Future<dynamic> get(
    String endpoint, {
    Map<String, String>? headers,
  }) async {
    return _sendRequest(
      method: 'GET',
      endpoint: endpoint,
      headers: headers,
    );
  }

  /// Performs HTTP POST request
  Future<dynamic> post(
    String endpoint, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    return _sendRequest(
      method: 'POST',
      endpoint: endpoint,
      body: body,
      headers: headers,
    );
  }

  /// Performs HTTP PUT request
  Future<dynamic> put(
    String endpoint, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    return _sendRequest(
      method: 'PUT',
      endpoint: endpoint,
      body: body,
      headers: headers,
    );
  }

  /// Performs HTTP PATCH request
  Future<dynamic> patch(
    String endpoint, {
    dynamic body,
    Map<String, String>? headers,
  }) async {
    return _sendRequest(
      method: 'PATCH',
      endpoint: endpoint,
      body: body,
      headers: headers,
    );
  }

  /// Performs HTTP DELETE request
  Future<dynamic> delete(
    String endpoint, {
    Map<String, String>? headers,
  }) async {
    return _sendRequest(
      method: 'DELETE',
      endpoint: endpoint,
      headers: headers,
    );
  }

  Future<dynamic> _sendRequest({
    required String method,
    required String endpoint,
    dynamic body,
    Map<String, String>? headers,
  }) async {
    final uri = Uri.parse('$baseUrl$endpoint');

    try {
      final request = await _httpClient.openUrl(method, uri).timeout(timeout);

      // Default request headers
      request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers.set('X-Client-App', AppConfig.appName);
      request.headers.set('X-Client-Version', AppConfig.appVersion);

      if (_authToken != null) {
        request.headers
            .set(HttpHeaders.authorizationHeader, 'Bearer $_authToken');
      }

      if (headers != null) {
        headers.forEach((key, value) {
          request.headers.set(key, value);
        });
      }

      if (body != null) {
        final payload = jsonEncode(body);
        request.write(payload);
      }

      final response = await request.close().timeout(timeout);
      final responseBody = await response.transform(utf8.decoder).join();

      return _handleResponse(response.statusCode, responseBody);
    } on SocketException catch (e) {
      throw NetworkException(
        'Unable to reach backend API at $baseUrl: ${e.message}',
      );
    } on TimeoutException {
      throw NetworkException(
        'Request to $endpoint timed out after ${timeout.inSeconds}s.',
      );
    } on HandshakeException catch (e) {
      throw NetworkException('TLS/SSL Handshake failed: ${e.message}');
    } catch (e) {
      if (e is AppException) rethrow;
      throw AppException('Unexpected error during API communication: $e');
    }
  }

  dynamic _handleResponse(int statusCode, String responseBody) {
    dynamic parsedJson;
    if (responseBody.isNotEmpty) {
      try {
        parsedJson = jsonDecode(responseBody);
      } catch (_) {
        parsedJson = responseBody;
      }
    }

    if (statusCode >= 200 && statusCode < 300) {
      return parsedJson;
    }

    final message = (parsedJson is Map && parsedJson.containsKey('detail'))
        ? parsedJson['detail'].toString()
        : 'HTTP Error $statusCode: $responseBody';

    if (statusCode == 401 || statusCode == 403) {
      throw AuthenticationException(message);
    }

    if (statusCode == 404) {
      throw AppException(message, code: 'NOT_FOUND');
    }

    if (statusCode == 422 || statusCode == 400) {
      throw AppException(message, code: 'VALIDATION_ERROR');
    }

    throw AppException(message, code: 'SERVER_ERROR_$statusCode');
  }

  void close() {
    _httpClient.close();
  }
}
