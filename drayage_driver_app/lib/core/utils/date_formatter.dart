/// Helper class for formatted presentation of dates and times in port operations.
class DateFormatter {
  static String formatTime(DateTime dateTime) {
    final hour = dateTime.hour.toString().padLeft(2, '0');
    final minute = dateTime.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  static String formatDateTime(DateTime dateTime) {
    final year = dateTime.year;
    final month = dateTime.month.toString().padLeft(2, '0');
    final day = dateTime.day.toString().padLeft(2, '0');
    final time = formatTime(dateTime);
    return '$year-$month-$day $time';
  }

  static String formatDuration(Duration duration) {
    if (duration.inMinutes < 60) {
      return '${duration.inMinutes} mins';
    }
    final hours = duration.inHours;
    final mins = duration.inMinutes % 60;
    return '${hours}h ${mins}m';
  }
}
