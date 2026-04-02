import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'screens/home/home_screen.dart';
import 'screens/search/search_screen.dart';
import 'screens/watchlist/watchlist_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/search',
    routes: [
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          GoRoute(path: '/search', builder: (c, s) => const SearchScreen()),
          GoRoute(path: '/watchlist', builder: (c, s) => const WatchlistScreen()),
        ],
      ),
      GoRoute(path: '/login', builder: (c, s) => const LoginScreen()),
      GoRoute(path: '/register', builder: (c, s) => const RegisterScreen()),
    ],
  );
});
