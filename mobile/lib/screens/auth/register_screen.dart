import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;

  Future<void> _register() async {
    setState(() => _loading = true);
    try {
      await apiService.register(_emailCtrl.text.trim(), _passCtrl.text);
      if (mounted) context.go('/search');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Kayıt başarısız: $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Kayıt Ol')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(controller: _emailCtrl, keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'E-posta', prefixIcon: Icon(Icons.email))),
            const SizedBox(height: 12),
            TextField(controller: _passCtrl, obscureText: true,
                decoration: const InputDecoration(labelText: 'Şifre', prefixIcon: Icon(Icons.lock))),
            const SizedBox(height: 24),
            SizedBox(width: double.infinity,
              child: FilledButton(
                onPressed: _loading ? null : _register,
                child: _loading ? const CircularProgressIndicator(color: Colors.white) : const Text('Kaydol'),
              ),
            ),
            TextButton(onPressed: () => context.go('/login'), child: const Text('Zaten hesabın var mı? Giriş yap')),
          ],
        ),
      ),
    );
  }
}
