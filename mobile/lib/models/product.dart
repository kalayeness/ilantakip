class Product {
  final String platform;
  final String externalId;
  final String title;
  final double price;
  final String currency;
  final String url;
  final String? imageUrl;
  final bool isSecondhand;
  final bool inStock;
  final String? seller;
  final String? location;

  const Product({
    required this.platform,
    required this.externalId,
    required this.title,
    required this.price,
    required this.currency,
    required this.url,
    this.imageUrl,
    required this.isSecondhand,
    required this.inStock,
    this.seller,
    this.location,
  });

  factory Product.fromJson(Map<String, dynamic> json) => Product(
        platform: json['platform'],
        externalId: json['external_id'],
        title: json['title'],
        price: (json['price'] as num).toDouble(),
        currency: json['currency'] ?? 'TRY',
        url: json['url'],
        imageUrl: json['image_url'],
        isSecondhand: json['is_secondhand'] ?? false,
        inStock: json['in_stock'] ?? true,
        seller: json['seller'],
        location: json['location'],
      );

  String get formattedPrice =>
      '${price.toStringAsFixed(0).replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]}.')} TL';

  String get platformLabel {
    const labels = {
      'trendyol': 'Trendyol',
      'hepsiburada': 'Hepsiburada',
      'sahibinden': 'Sahibinden',
    };
    return labels[platform] ?? platform;
  }
}

class WatchlistItem {
  final int id;
  final String searchName;
  final String? searchUrl;
  final String? keywords;
  final double? minPrice;
  final double? maxPrice;
  final double? targetPrice;
  final String? platforms;
  final bool active;

  const WatchlistItem({
    required this.id,
    required this.searchName,
    this.searchUrl,
    this.keywords,
    this.minPrice,
    this.maxPrice,
    this.targetPrice,
    this.platforms,
    required this.active,
  });

  factory WatchlistItem.fromJson(Map<String, dynamic> json) => WatchlistItem(
        id: json['id'],
        searchName: json['search_name'],
        searchUrl: json['search_url'],
        keywords: json['keywords'],
        minPrice: json['min_price']?.toDouble(),
        maxPrice: json['max_price']?.toDouble(),
        targetPrice: json['target_price']?.toDouble(),
        platforms: json['platforms'],
        active: json['active'] ?? true,
      );
}
