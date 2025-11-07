import mss
import mouse
import time

print("🖱️ Postavi kursor u GORNJI LEVI ugao BVMS video prozora i klikni levi taster miša...")
while not mouse.is_pressed():
    time.sleep(0.1)

x1, y1 = mouse.get_position()
print(f"Gornji levi ugao: ({x1}, {y1})")

time.sleep(1)

print("\n🖱️ Sada postavi kursor u DONJI DESNI ugao istog prozora i klikni levi taster miša...")
while not mouse.is_pressed():
    time.sleep(0.1)

x2, y2 = mouse.get_position()
print(f"Donji desni ugao: ({x2}, {y2})")

# Izračunavanje širine i visine
width = x2 - x1
height = y2 - y1

# Ispis rezultata u formatu za config.json
print("\n📏 Rezultat (kopiraj u config.json):\n")
print("{")
print(f'    "top": {y1},')
print(f'    "left": {x1},')
print(f'    "width": {width},')
print(f'    "height": {height}')
print("}")

print("\n✅ Završeno! Kopiraj prikazani blok u svoj config.json fajl.")
