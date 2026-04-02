import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/product.dart';
import '../../services/api_service.dart';

final watchlistProvider = FutureProvider<List<WatchlistItem>>((ref) async {
  return apiService.getWatchlist();
});

class WatchlistScreen extends ConsumerWidget {
  const WatchlistScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final watchlistAsync = ref.watch(watchlistProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Takip Listem')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddDialog(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Filtre Ekle'),
      ),
      body: watchlistAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Hata: $e')),
        data: (items) => items.isEmpty
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.bookmark_border, size: 64, color: Colors.grey),
                    const SizedBox(height: 16),
                    Text('Henüz takip listesi yok', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    const Text('Ürün veya ilan araması ekleyin,\nyeni ilanlar gelince bildirim alın',
                        textAlign: TextAlign.center),
                  ],
                ),
              )
            : ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: items.length,
                itemBuilder: (context, i) => WatchlistCard(
                  item: items[i],
                  onDelete: () async {
                    await apiService.removeFromWatchlist(items[i].id);
                    ref.invalidate(watchlistProvider);
                  },
                ),
              ),
      ),
    );
  }

  void _showAddDialog(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => AddWatchlistSheet(onAdded: () => ref.invalidate(watchlistProvider)),
    );
  }
}

class WatchlistCard extends StatelessWidget {
  final WatchlistItem item;
  final VoidCallback onDelete;

  const WatchlistCard({super.key, required this.item, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: const CircleAvatar(child: Icon(Icons.notifications)),
        title: Text(item.searchName, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (item.keywords != null && item.keywords!.isNotEmpty)
              Text('🎨 ${item.keywords}', style: const TextStyle(fontSize: 12)),
            if (item.maxPrice != null)
              Text('💰 Max: ${item.maxPrice!.toStringAsFixed(0)} TL', style: const TextStyle(fontSize: 12)),
            if (item.targetPrice != null)
              Text('🎯 Hedef: ${item.targetPrice!.toStringAsFixed(0)} TL',
                  style: const TextStyle(fontSize: 12, color: Colors.green)),
          ],
        ),
        isThreeLine: true,
        trailing: IconButton(
          icon: const Icon(Icons.delete_outline, color: Colors.red),
          onPressed: onDelete,
        ),
      ),
    );
  }
}

class AddWatchlistSheet extends StatefulWidget {
  final VoidCallback onAdded;
  const AddWatchlistSheet({super.key, required this.onAdded});

  @override
  State<AddWatchlistSheet> createState() => _AddWatchlistSheetState();
}

class _AddWatchlistSheetState extends State<AddWatchlistSheet> {
  final _nameCtrl = TextEditingController();
  final _urlCtrl = TextEditingController();
  final _keywordsCtrl = TextEditingController();
  final _maxPriceCtrl = TextEditingController();
  final _targetPriceCtrl = TextEditingController();
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Takip Filtresi Ekle', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          TextField(controller: _nameCtrl, decoration: const InputDecoration(labelText: 'İsim *', hintText: 'MacBook Mavi')),
          const SizedBox(height: 8),
          TextField(controller: _urlCtrl, decoration: const InputDecoration(labelText: 'Sahibinden URL (opsiyonel)', hintText: 'https://www.sahibinden.com/...')),
          const SizedBox(height: 8),
          TextField(controller: _keywordsCtrl, decoration: const InputDecoration(labelText: 'Anahtar Kelimeler', hintText: 'gök mavisi, sky blue')),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: TextField(controller: _maxPriceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Max Fiyat (TL)'))),
              const SizedBox(width: 8),
              Expanded(child: TextField(controller: _targetPriceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Hedef Fiyat (TL)'))),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _loading ? null : _submit,
              child: _loading ? const CircularProgressIndicator(color: Colors.white) : const Text('Ekle'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    if (_nameCtrl.text.trim().isEmpty) return;
    setState(() => _loading = true);
    try {
      await apiService.addToWatchlist(
        searchName: _nameCtrl.text.trim(),
        searchUrl: _urlCtrl.text.trim().isEmpty ? null : _urlCtrl.text.trim(),
        keywords: _keywordsCtrl.text.trim().isEmpty ? null : _keywordsCtrl.text.trim(),
        maxPrice: double.tryParse(_maxPriceCtrl.text),
        targetPrice: double.tryParse(_targetPriceCtrl.text),
      );
      widget.onAdded();
      if (mounted) Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Hata: $e'), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
}
