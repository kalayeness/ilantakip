import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_service.dart';

class NotificationService {
  static final _localNotifications = FlutterLocalNotificationsPlugin();

  static Future<void> init() async {
    // İzin iste
    await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);

    // Local notifications başlat
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _localNotifications.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );

    // FCM token al ve sunucuya gönder
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
      try {
        await apiService.updateFcmToken(token);
      } catch (_) {}
    }

    // Token yenilenince güncelle
    FirebaseMessaging.instance.onTokenRefresh.listen((token) async {
      try {
        await apiService.updateFcmToken(token);
      } catch (_) {}
    });

    // Uygulama açıkken gelen bildirimler
    FirebaseMessaging.onMessage.listen((message) {
      _showLocalNotification(message);
    });
  }

  static Future<void> _showLocalNotification(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

    await _localNotifications.show(
      notification.hashCode,
      notification.title,
      notification.body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'ilantakip_channel',
          'İlan Takip Bildirimleri',
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
    );
  }
}
