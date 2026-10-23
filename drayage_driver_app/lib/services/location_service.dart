import '../models/location_update.dart';
import 'mock_data_service.dart';

/// GPS location service interface for internal port tracking.
class LocationService {
  bool _isTracking = true;

  bool get isTracking => _isTracking;

  void toggleTracking(bool enable) {
    _isTracking = enable;
  }

  /// Obtains current GPS coordinates
  Future<LocationUpdate> getCurrentLocation() async {
    await Future.delayed(const Duration(milliseconds: 150));
    return MockDataService.getMockLocation();
  }
}
