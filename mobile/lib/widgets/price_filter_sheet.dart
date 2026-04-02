import 'package:flutter/material.dart';
import '../screens/search/search_screen.dart';

class PriceFilterSheet extends StatefulWidget {
  final SearchFilter filter;
  final Function(SearchFilter) onApply;

  const PriceFilterSheet({super.key, required this.filter, required this.onApply});

  @override
  State<PriceFilterSheet> createState() => _PriceFilterSheetState();
}

class _PriceFilterSheetState extends State<PriceFilterSheet> {
  late bool _secondhandOnly;
  late bool _newOnly;
  final _minCtrl = TextEditingController();
  final _maxCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _secondhandOnly = widget.filter.secondhandOnly;
    _newOnly = widget.filter.newOnly;
    if (widget.filter.minPrice != null) _minCtrl.text = widget.filter.minPrice!.toStringAsFixed(0);
    if (widget.filter.maxPrice != null) _maxCtrl.text = widget.filter.maxPrice!.toStringAsFixed(0);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Filtrele', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          const Text('Ürün Tipi', style: TextStyle(fontWeight: FontWeight.w600)),
          CheckboxListTile(title: const Text('Sadece 2. El'), value: _secondhandOnly,
              onChanged: (v) => setState(() { _secondhandOnly = v!; if (v) _newOnly = false; })),
          CheckboxListTile(title: const Text('Sadece Sıfır'), value: _newOnly,
              onChanged: (v) => setState(() { _newOnly = v!; if (v) _secondhandOnly = false; })),
          const SizedBox(height: 8),
          const Text('Fiyat Aralığı (TL)', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: TextField(controller: _minCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Min'))),
              const SizedBox(width: 12),
              Expanded(child: TextField(controller: _maxCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Max'))),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: OutlinedButton(
                onPressed: () {
                  widget.onApply(const SearchFilter());
                  Navigator.pop(context);
                },
                child: const Text('Temizle'),
              )),
              const SizedBox(width: 12),
              Expanded(child: FilledButton(
                onPressed: () {
                  widget.onApply(SearchFilter(
                    secondhandOnly: _secondhandOnly,
                    newOnly: _newOnly,
                    minPrice: double.tryParse(_minCtrl.text),
                    maxPrice: double.tryParse(_maxCtrl.text),
                  ));
                  Navigator.pop(context);
                },
                child: const Text('Uygula'),
              )),
            ],
          ),
        ],
      ),
    );
  }
}
