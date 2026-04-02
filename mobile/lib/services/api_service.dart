import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/product.dart';

class ApiService {
  static const _baseUrl = 'http://YOUR_SERVER_IP:8000'; // Sunucu adresi
  static const _storage = FlutterSecureStorage();

  late final Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(baseUrl: _baseUrl, connectTimeout: const Duration(seconds: 15)));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'auth_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));
  }

  // Auth
  Future<String> register(String email, String password) async {
    final res = await _dio.post('/auth/register', data: {'email': email, 'password': password});
    final token = res.data['access_token'];
    await _storage.write(key: 'auth_token', value: token);
    return token;
  }

  Future<String> login(String email, String password) async {
    final res = await _dio.post('/auth/login', data: {'email': email, 'password': password});
    final token = res.data['access_token'];
    await _storage.write(key: 'auth_token', value: token);
    return token;
  }

  Future<void> logout() async {
    await _storage.delete(key: 'auth_token');
  }

  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: 'auth_token');
    return token != null;
  }

  Future<void> updateFcmToken(String fcmToken) async {
    await _dio.post('/auth/fcm-token', data: {'token': fcmToken});
  }

  // Arama
  Future<List<Product>> search({
    required String query,
    String? platforms,
    bool secondhandOnly = false,
    bool newOnly = false,
    double? minPrice,
    double? maxPrice,
    int maxPages = 2,
  }) async {
    final params = <String, dynamic>{
      'q': query,
      if (platforms != null) 'platforms': platforms,
      if (secondhandOnly) 'secondhand_only': true,
      if (newOnly) 'new_only': true,
      if (minPrice != null) 'min_price': minPrice,
      if (maxPrice != null) 'max_price': maxPrice,
      'max_pages': maxPages,
    };
    final res = await _dio.get('/search', queryParameters: params);
    return (res.data as List).map((e) => Product.fromJson(e)).toList();
  }

  // Takip listesi
  Future<List<WatchlistItem>> getWatchlist() async {
    final res = await _dio.get('/watchlist');
    return (res.data as List).map((e) => WatchlistItem.fromJson(e)).toList();
  }

  Future<WatchlistItem> addToWatchlist({
    required String searchName,
    String? searchUrl,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    double? targetPrice,
    String? platforms,
  }) async {
    final res = await _dio.post('/watchlist', data: {
      'search_name': searchName,
      if (searchUrl != null) 'search_url': searchUrl,
      if (keywords != null) 'keywords': keywords,
      if (minPrice != null) 'min_price': minPrice,
      if (maxPrice != null) 'max_price': maxPrice,
      if (targetPrice != null) 'target_price': targetPrice,
      if (platforms != null) 'platforms': platforms,
    });
    return WatchlistItem.fromJson(res.data);
  }

  Future<void> removeFromWatchlist(int id) async {
    await _dio.delete('/watchlist/$id');
  }
}

final apiService = ApiService();
