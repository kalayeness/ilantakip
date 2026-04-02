import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;

  Future<void> _login() async {
    setState(() => _loading = true);
    try {
      await apiService.login(_emailCtrl.text.trim(), _passCtrl.text);
      if (mounted) context.go('/search');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Giriş başarısız: $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Giriş Yap')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.notifications_active, size: 80, color: Color(0xFF6C63FF)),
            const SizedBox(height: 24),
            Text('İlan Takip', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 32),
            TextField(controller: _emailCtrl, keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'E-posta', prefixIcon: Icon(Icons.email))),
            const SizedBox(height: 12),
            TextField(controller: _passCtrl, obscureText: true,
                decoration: const InputDecoration(labelText: 'Şifre', prefixIcon: Icon(Icons.lock))),
            const SizedBox(height: 24),
            SizedBox(width: double.infinity,
              child: FilledButton(
                onPressed: _loading ? null : _login,
                child: _loading ? const CircularProgressIndicator(color: Colors.white) : const Text('Giriş Yap'),
              ),
            ),
            const SizedBox(height: 12),
            TextButton(onPressed: () => context.go('/register'), child: const Text('Hesap yok mu? Kaydol')),
          ],
        ),
      ),
    );
  }
}
