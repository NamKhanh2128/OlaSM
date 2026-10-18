import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

/// Centralized permission guard for microphone, location, and notifications.
class PermissionGuard {
  /// Request microphone permission with rationale dialog.
  /// Returns true if granted.
  static Future<bool> ensureMicrophone(BuildContext context) async {
    var status = await Permission.microphone.status;
    if (status.isGranted) return true;

    if (status.isDenied) {
      status = await Permission.microphone.request();
      if (status.isGranted) return true;
    }

    if (status.isPermanentlyDenied && context.mounted) {
      await showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: const Color(0xFF1E222D),
          title: const Text(
            'Cần quyền Microphone',
            style: TextStyle(color: Colors.white),
          ),
          content: const Text(
            'OlaSM cần quyền truy cập microphone để nhận diện giọng nói '
            'và kết nối với tổng đài viên AI. Vui lòng bật trong Cài đặt.',
            style: TextStyle(color: Colors.white70),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Hủy'),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                openAppSettings();
              },
              child: const Text('Mở Cài đặt'),
            ),
          ],
        ),
      );
    }

    return false;
  }

  /// Request location permission for pickup point detection.
  static Future<bool> ensureLocation(BuildContext context) async {
    var status = await Permission.locationWhenInUse.status;
    if (status.isGranted) return true;

    if (status.isDenied) {
      status = await Permission.locationWhenInUse.request();
      if (status.isGranted) return true;
    }

    if (status.isPermanentlyDenied && context.mounted) {
      await showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: const Color(0xFF1E222D),
          title: const Text(
            'Cần quyền Vị trí',
            style: TextStyle(color: Colors.white),
          ),
          content: const Text(
            'OlaSM cần vị trí để tự động xác định điểm đón xe chính xác.',
            style: TextStyle(color: Colors.white70),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Bỏ qua'),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                openAppSettings();
              },
              child: const Text('Mở Cài đặt'),
            ),
          ],
        ),
      );
    }

    return false;
  }

  /// Request all required permissions at app startup.
  static Future<Map<Permission, PermissionStatus>> requestAll() async {
    return await [
      Permission.microphone,
      Permission.locationWhenInUse,
    ].request();
  }
}
