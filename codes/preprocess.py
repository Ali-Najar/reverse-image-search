# preprocess.py
"""
Step-1 pipeline: read → denoise → enhance → detect & align face → save crop
Matches the “Input Handling & Pre-processing” requirements in the project brief. :contentReference[oaicite:0]{index=0}
"""

from pathlib import Path
import cv2
import numpy as np
import face_recognition
# import torch
# from facenet_pytorch import MTCNN

# _DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
# _mtcnn = MTCNN(image_size=160, margin=14, device=_DEVICE)

def _denoise(img_bgr: np.ndarray) -> np.ndarray:
    """Edge-preserving bilateral filter."""
    return cv2.bilateralFilter(img_bgr, d=5, sigmaColor=75, sigmaSpace=75)


def _adjust_contrast_brightness(img_bgr: np.ndarray, gamma: float = 1.2) -> np.ndarray:
    """CLAHE in LAB colour space + gamma correction."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    img_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # gamma LUT
    lut = np.array([((i / 255.0) ** (1 / gamma)) * 255 for i in range(256)]).astype(
        "uint8"
    )
    return cv2.LUT(img_clahe, lut)

def _extract_faces(image):
    face_locations = face_recognition.face_locations(image)
    
    assert len(face_locations) == 1, "Expected exactly one face in the image."
    
    top, right, bottom, left = face_locations[0]
    face_image = image[top:bottom, left:right]
    return face_image


def prepare_face(input_path):
    img_bgr = cv2.imread(str(input_path))
    if img_bgr is None:
        raise ValueError(f"Could not read image: {input_path}")

    # 2. Denoise + enhance
    img_bgr = _denoise(img_bgr)
    img_bgr = _extract_faces(img_bgr)
    # img_bgr = _adjust_contrast_brightness(img_bgr)

    # 3. Detect & align (expects RGB PIL image)
    # img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    # aligned = _mtcnn(Image.fromarray(img_rgb))

    # if aligned is None:
    #     print(f"[WARN] No face found in {input_path}")
    #     return None

    # 4. Save crop
    # aligned_np = (aligned.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
    # out_name = output_name or input_path.stem
    # out_path = output_dir / f"{out_name}_aligned.png"
    # cv2.imwrite(str(out_path), cv2.cvtColor(aligned_np, cv2.COLOR_RGB2BGR))
    # cv2.imwrite(str(out_path), img_bgr)
    return img_bgr


# --------------------------------------------------
# Optional CLI
# --------------------------------------------------
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Step-1 face pre-processing")
    parser.add_argument("--input", help="Path to input image")
    parser.add_argument(
        "--outdir", "-o", default="preprocessed", help="Destination directory"
    )
    args = parser.parse_args()

    saved = prepare_face(args.input, args.outdir)
    cv2.imwrite("image.png", saved)
    # if saved:
    #     print(f"✅ Saved aligned face → {saved}")
    # else:
    #     sys.exit(1)
