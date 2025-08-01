from utils import upload_image_imgbb
API_KEY = "9e1aef25f19ff71c6163cf7659cc644a"

url = upload_image_imgbb(API_KEY, "/home/xulei/shayan/other/reverse-image-search/data/images/aster.jpg")
print(f"Image uploaded to: {url}")