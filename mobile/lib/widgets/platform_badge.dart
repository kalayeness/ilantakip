import 'package:flutter/material.dart';

class PlatformBadge extends StatelessWidget {
  final String platform;
  const PlatformBadge({super.key, required this.platform});

  static const _colors = {
    'trendyol': Color(0xFFFF6000),
    'hepsiburada': Color(0xFFFF6000),
    'sahibinden': Color(0xFF1A73E8),
  };

  static const _labels = {
    'trendyol': 'Trendyol',
    'hepsiburada': 'Hepsiburada',
    'sahibinden': 'Sahibinden',
  };

  @override
  Widget build(BuildContext context) {
    final color = _colors[platform] ?? Colors.grey;
    final label = _labels[platform] ?? platform;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
