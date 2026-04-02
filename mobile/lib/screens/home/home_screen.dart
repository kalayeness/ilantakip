import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: location.startsWith('/watchlist') ? 1 : 0,
        onDestinationSelected: (i) {
          if (i == 0) context.go('/search');
          if (i == 1) context.go('/watchlist');
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: 'Ara'),
          NavigationDestination(icon: Icon(Icons.bookmark), label: 'Takip'),
        ],
      ),
    );
  }
}
