-- Populate products table with sample data for Cloud SQL
-- This script adds the original 9 products plus 6 additional onesthe

INSERT INTO products (id, name, description, picture, price_usd_currency_code, price_usd_units, price_usd_nanos, categories) VALUES
-- Original 9 products
('OLJCESPC7Z', 'Sunglasses', 'Add a modern touch to your outfits with these sleek aviator sunglasses.', 'https://glassyeyewear.com/cdn/shop/files/walker-mblk-rm-polar-34.jpg?v=1705618525&width=1000', 'USD', 19, 990000000, 'accessories'),
('66VCHSJNUP', 'Tank Top', 'Perfectly cropped cotton tank, with a scooped neckline.', 'https://asrv.com/cdn/shop/files/SPACEGREY_TankTop1_1600x.jpg?v=1710530514', 'USD', 18, 990000000, 'clothing,tanks'),
('1YMWWN1N4O', 'Watch', 'This gold-tone stainless steel watch will work with most of your outfits.', '/static/img/products/watch.jpg', 'USD', 109, 990000000, 'accessories'),
('L9ECAV7KIM', 'Loafers', 'A neat addition to your summer wardrobe.', '/static/img/products/loafers.jpg', 'USD', 89, 990000000, 'footwear'),
('2ZYFJ3GM2N', 'Hairdryer', 'This lightweight hairdryer has 3 heat and speed settings. It''s perfect for drying your hair quickly.', '/static/img/products/hairdryer.jpg', 'USD', 24, 990000000, 'hair,beauty'),
('0PUK6V6EV0', 'Candle Holder', 'This small but stylish candle holder is an excellent addition to your home decor.', '/static/img/products/candle-holder.jpg', 'USD', 18, 990000000, 'decor,home'),
('LS4PSXUNUM', 'Salt & Pepper Shakers', 'Add some flavor to your kitchen.', '/static/img/products/salt-and-pepper-shakers.jpg', 'USD', 18, 990000000, 'kitchen'),
('9SIQT8TOJO', 'Bamboo Glass Jar', 'This bamboo glass jar can hold 57 oz (1.7l) and is perfect for any kitchen counter.', '/static/img/products/bamboo-glass-jar.jpg', 'USD', 5, 990000000, 'kitchen'),
('6E92ZMYYFZ', 'Mug', 'A simple mug with a mustard interior.', '/static/img/products/mug.jpg', 'USD', 8, 990000000, 'kitchen'),
('CAMERA001', 'Vintage Camera', 'Capture life''s precious moments with this retro-style camera perfect for photography enthusiasts.', 'https://dfjx2uxqg3cgi.cloudfront.net/img/photo/35737/35737_00_2x.jpg?20150621115429', 'USD', 89, 990000000, 'electronics,photography'),
('BACKPACK01', 'Travel Backpack', 'Durable and spacious backpack ideal for hiking, traveling, and everyday adventures.', 'https://cdn.thewirecutter.com/wp-content/media/2024/04/carryontravelbackpacks-2048px-0187.jpg?auto=webp&quality=75&width=1024', 'USD', 67, 990000000, 'bags,travel'),
('NOTEBOOK1', 'Leather Notebook', 'Premium leather-bound notebook perfect for journaling, sketching, or taking notes.', 'https://m.media-amazon.com/images/I/81kr4gvE8xL.jpg', 'USD', 23, 990000000, 'stationery,office'),
('SNEAKERS1', 'Running Sneakers', 'Comfortable and lightweight running shoes designed for performance and style.', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSPLnQxWxWCw0EJOW3VEwkNTLLc3x5AzfL_aw&s', 'USD', 78, 990000000, 'footwear,sports'),
('PLANTPOT1', 'Ceramic Plant Pot', 'Beautiful ceramic pot perfect for your favorite indoor plants and succulents.', 'https://m.media-amazon.com/images/I/713ZvA5hL9L.jpg', 'USD', 15, 990000000, 'decor,home,garden'),
('TSHIRT001', 'Cotton T-Shirt', 'Soft and comfortable 100% cotton t-shirt available in multiple colors.', 'https://joesusa.com/cdn/shop/files/athleticheather-front__83530__24374_8135__17315.1730584884.1280.1280.jpg?v=1743029922', 'USD', 24, 990000000, 'clothing,casual')

ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  picture = EXCLUDED.picture,
  price_usd_currency_code = EXCLUDED.price_usd_currency_code,
  price_usd_units = EXCLUDED.price_usd_units,
  price_usd_nanos = EXCLUDED.price_usd_nanos,
  categories = EXCLUDED.categories; 