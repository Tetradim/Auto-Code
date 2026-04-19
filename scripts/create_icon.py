from PIL import Image, ImageDraw

sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Emerald green gradient circle
    draw.ellipse([0, 0, size-1, size-1], fill=(16, 185, 129, 255))
    draw.ellipse([2, 2, size-3, size-3], fill=(34, 197, 94, 255))
    images.append(img)

images[0].save('app.ico', format='ICO', sizes=[(s, s) for s in sizes])