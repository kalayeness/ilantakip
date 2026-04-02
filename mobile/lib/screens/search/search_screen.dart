import 'package:flutter/flutter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../models/product.dart';
import '../../services/api_service.dart';
import '../../widgets/platform_badge.dart';
import '../../widgets/price_filter_sheet.dart';

final searchQueryProvider = StateProvider<String>((ref) => '');
final searchResultsProvider = StateProvider<List<Product>>((ref) => []);
final searchLoadingProvider = StateProvider<bool>((ref) => false);
final filterProvider = StateProvider<SearchFilter>((ref) => const SearchFilter());

class SearchFilter {
  final bool secondhandOnly;
  final bool newOnly;
  final double? minPrice;
  final double? maxPrice;
  final Set<String> platforms;

  const SearchFilter({
    this.secondhandOnly = false,
    this.newOnly = false,
    this.minPrice,
    this.maxPrice,
    this.platforms = const {},
  });
}

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();

  Future<void> _search() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;

    ref.read(searchLoadingProvider.notifier).state = true;
    ref.read(searchResultsProvider.notifier).state = [];

    final filter = ref.read(filterProvider);
    try {
      final results = await apiService.search(
        query: query,
        secondhandOnly: filter.secondhandOnly,
        newOnly: filter.newOnly,
        minPrice: filter.minPrice,
        maxPrice: filter.maxPrice,
        platforms: filter.platforms.isEmpty ? null : filter.platforms.join(','),
      );
      ref.read(searchResultsProvider.notifier).state = results;
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Hata: $e'), backgroundColor: Colors.red),
      );
    } finally {
      ref.read(searchLoadingProvider.notifier).state = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchResultsProvider);
    final loading = ref.watch(searchLoadingProvider);
    final filter = ref.watch(filterProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('İlan Takip'),
        actions: [
          IconButton(
            icon: Badge(
              isLabelVisible: filter.secondhandOnly || filter.newOnly ||
                  filter.minPrice != null || filter.maxPrice != null,
              child: const Icon(Icons.tune),
            ),
            onPressed: () => _showFilterSheet(context),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: 'MacBook, iPhone, araba...',
                      prefixIcon: Icon(Icons.search),
                    ),
                    textInputAction: TextInputAction.search,
                    onSubmitted: (_) => _search(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: loading ? null : _search,
                  child: loading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('Ara'),
                ),
              ],
            ),
          ),
          if (filter.secondhandOnly || filter.newOnly)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  if (filter.secondhandOnly)
                    Chip(label: const Text('Sadece 2. El'), onDeleted: () {
                      ref.read(filterProvider.notifier).state = SearchFilter(newOnly: filter.newOnly, minPrice: filter.minPrice, maxPrice: filter.maxPrice);
                    }),
                  if (filter.newOnly)
                    Chip(label: const Text('Sadece Sıfır'), onDeleted: () {
                      ref.read(filterProvider.notifier).state = SearchFilter(secondhandOnly: filter.secondhandOnly, minPrice: filter.minPrice, maxPrice: filter.maxPrice);
                    }),
                ],
              ),
            ),
          if (results.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  Text('${results.length} sonuç', style: Theme.of(context).textTheme.bodySmall),
                  const Spacer(),
                  Text('En ucuzdan sıralı', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : results.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.search, size: 64, color: Colors.grey),
                            const SizedBox(height: 16),
                            Text('Arama yapın', style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 8),
                            const Text('Trendyol, Hepsiburada ve Sahibinden\naynı anda taranır', textAlign: TextAlign.center),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        itemCount: results.length,
                        itemBuilder: (context, i) => ProductCard(product: results[i]),
                      ),
          ),
        ],
      ),
    );
  }

  void _showFilterSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => PriceFilterSheet(
        filter: ref.read(filterProvider),
        onApply: (f) => ref.read(filterProvider.notifier).state = f,
      ),
    );
  }
}

class ProductCard extends ConsumerWidget {
  final Product product;
  const ProductCard({super.key, required this.product});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => launchUrl(Uri.parse(product.url), mode: LaunchMode.externalApplication),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: product.imageUrl != null
                    ? CachedNetworkImage(
                        imageUrl: product.imageUrl!,
                        width: 72, height: 72, fit: BoxFit.cover,
                        errorWidget: (_, __, ___) => const Icon(Icons.image, size: 72),
                      )
                    : const SizedBox(width: 72, height: 72, child: Icon(Icons.image, size: 40)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(product.title, maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w500)),
                    const SizedBox(height: 4),
                    Text(product.formattedPrice,
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.primary)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        PlatformBadge(platform: product.platform),
                        if (product.isSecondhand) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.orange.shade100,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text('2. El', style: TextStyle(fontSize: 11, color: Colors.orange)),
                          ),
                        ],
                        if (product.location != null) ...[
                          const SizedBox(width: 6),
                          Icon(Icons.location_on, size: 12, color: Colors.grey.shade500),
                          Text(product.location!, style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Colors.grey.shade400),
            ],
          ),
        ),
      ),
    );
  }
}
