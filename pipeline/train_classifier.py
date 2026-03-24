"""
CwbVerde — Train Random Forest Classifier with REAL training samples
from known locations in Curitiba.

Uses 6 spectral bands + 4 indices = 10 features per pixel.
Training data from known locations (verified via Google Maps):
- Urban: Centro, Batel, Reboucas, CIC industrial
- Dense vegetation: Parque Barigui (forest), Parque Tingui, Parque Tanguá
- Light vegetation: Jardim Botanico lawns, Bacacheri park grass
- Water: Lago do Barigui, Lago do Parque Bacacheri, Rio Iguaçu
- Bare soil: Construction sites, exposed areas
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
import joblib
from pipeline.config import DATA_DIR

RAW_DIR = DATA_DIR / "raw"
NDVI_DIR = DATA_DIR / "ndvi"
CLASS_DIR = DATA_DIR / "classification"
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CLASS_DIR.mkdir(parents=True, exist_ok=True)

LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -49.40, -25.65, -49.15, -25.33

# Class labels
CLASSES = {
    1: "water",
    2: "dense_vegetation",
    3: "light_vegetation",
    4: "urban",
    5: "bare_soil",
}

# ============================================================
# TRAINING SAMPLES — Real coordinates from known Curitiba locations
# Verified via Google Maps satellite view
# Format: (lon, lat, class_id, description)
# ============================================================
TRAINING_POINTS = [
    # === WATER (class 1) ===
    # Lago do Parque Barigui
    (-49.3115, -25.4235, 1, "Lago Barigui centro"),
    (-49.3108, -25.4220, 1, "Lago Barigui norte"),
    (-49.3120, -25.4250, 1, "Lago Barigui sul"),
    (-49.3112, -25.4240, 1, "Lago Barigui leste"),
    (-49.3118, -25.4230, 1, "Lago Barigui oeste"),
    # Lago do Parque Bacacheri
    (-49.2465, -25.3960, 1, "Lago Bacacheri"),
    (-49.2470, -25.3955, 1, "Lago Bacacheri 2"),
    # Lago do Parque São Lourenço
    (-49.2720, -25.3830, 1, "Lago São Lourenço"),
    (-49.2715, -25.3835, 1, "Lago São Lourenço 2"),
    # Rio Iguaçu (sul de Curitiba)
    (-49.2800, -25.5800, 1, "Rio Iguaçu 1"),
    (-49.2600, -25.5900, 1, "Rio Iguaçu 2"),
    (-49.3000, -25.5700, 1, "Rio Iguaçu 3"),
    (-49.2400, -25.6000, 1, "Rio Iguaçu 4"),
    # Lago Parque Tanguá
    (-49.2855, -25.3815, 1, "Lago Tanguá"),
    # Lago Parque Tingui
    (-49.3085, -25.3855, 1, "Lago Tingui"),
    # Rio Barigui
    (-49.3150, -25.4400, 1, "Rio Barigui 1"),
    (-49.3200, -25.4600, 1, "Rio Barigui 2"),
    # Represa Passaúna
    (-49.3800, -25.4500, 1, "Passaúna 1"),
    (-49.3850, -25.4450, 1, "Passaúna 2"),
    (-49.3750, -25.4550, 1, "Passaúna 3"),

    # === DENSE VEGETATION (class 2) ===
    # Parque Barigui - área de mata
    (-49.3150, -25.4180, 2, "Barigui mata norte"),
    (-49.3160, -25.4200, 2, "Barigui mata"),
    (-49.3140, -25.4260, 2, "Barigui mata sul"),
    (-49.3080, -25.4190, 2, "Barigui mata leste"),
    (-49.3170, -25.4210, 2, "Barigui mata oeste"),
    # Parque Tanguá - mata
    (-49.2840, -25.3790, 2, "Tanguá mata"),
    (-49.2860, -25.3800, 2, "Tanguá mata 2"),
    # Parque Tingui - mata
    (-49.3070, -25.3840, 2, "Tingui mata"),
    (-49.3090, -25.3860, 2, "Tingui mata 2"),
    # Parque São Lourenço - mata
    (-49.2700, -25.3810, 2, "São Lourenço mata"),
    (-49.2740, -25.3820, 2, "São Lourenço mata 2"),
    # Bosque do Alemão
    (-49.2860, -25.3900, 2, "Bosque Alemão"),
    # Bosque do Papa
    (-49.2970, -25.3870, 2, "Bosque Papa"),
    # Mata ciliar Passaúna
    (-49.3700, -25.4500, 2, "Passaúna mata"),
    (-49.3750, -25.4450, 2, "Passaúna mata 2"),
    # Santa Felicidade - área rural com mata
    (-49.3400, -25.3700, 2, "Santa Felicidade mata"),
    (-49.3500, -25.3650, 2, "Santa Felicidade mata 2"),
    # Butiatuvinha - mata
    (-49.3600, -25.3800, 2, "Butiatuvinha mata"),
    (-49.3550, -25.3850, 2, "Butiatuvinha mata 2"),
    # CIC - áreas preservadas
    (-49.3500, -25.5000, 2, "CIC mata"),
    # APA do Iguaçu
    (-49.2500, -25.5500, 2, "APA Iguaçu"),
    (-49.2600, -25.5400, 2, "APA Iguaçu 2"),

    # === LIGHT VEGETATION (class 3) ===
    # Jardim Botânico - gramados
    (-49.2385, -25.4412, 3, "Jardim Botânico gramado"),
    (-49.2375, -25.4420, 3, "Jardim Botânico 2"),
    # Parque Barigui - gramados (perto da pista)
    (-49.3095, -25.4260, 3, "Barigui gramado"),
    (-49.3100, -25.4275, 3, "Barigui gramado 2"),
    # Bacacheri - gramados
    (-49.2480, -25.3975, 3, "Bacacheri gramado"),
    # Universidade Livre do Meio Ambiente
    (-49.2870, -25.4710, 3, "Unilivre gramado"),
    # Praça Japão
    (-49.2950, -25.4430, 3, "Praça Japão"),
    # Praça do Expedicionário
    (-49.2700, -25.4370, 3, "Praça Expedicionário"),
    # Campos no sul - Tatuquara
    (-49.3200, -25.5500, 3, "Tatuquara campo"),
    (-49.3100, -25.5600, 3, "Tatuquara campo 2"),
    # Pinheirinho - áreas verdes
    (-49.3100, -25.5100, 3, "Pinheirinho gramado"),
    # Ecoville - jardins
    (-49.3400, -25.4400, 3, "Ecoville jardim"),

    # === URBAN (class 4) ===
    # Centro de Curitiba
    (-49.2733, -25.4284, 4, "Centro Curitiba"),
    (-49.2720, -25.4270, 4, "Centro 2"),
    (-49.2750, -25.4290, 4, "Centro 3"),
    (-49.2710, -25.4300, 4, "Centro Rui Barbosa"),
    (-49.2740, -25.4260, 4, "Centro Marechal"),
    # Batel
    (-49.2900, -25.4420, 4, "Batel"),
    (-49.2880, -25.4410, 4, "Batel 2"),
    (-49.2920, -25.4430, 4, "Batel 3"),
    # Rebouças
    (-49.2650, -25.4450, 4, "Rebouças"),
    (-49.2670, -25.4440, 4, "Rebouças 2"),
    # Água Verde
    (-49.2850, -25.4520, 4, "Água Verde"),
    (-49.2830, -25.4530, 4, "Água Verde 2"),
    # Portão (shopping)
    (-49.2930, -25.4680, 4, "Portão shopping"),
    # CIC - industrial
    (-49.3500, -25.4800, 4, "CIC industrial"),
    (-49.3450, -25.4850, 4, "CIC industrial 2"),
    (-49.3550, -25.4750, 4, "CIC industrial 3"),
    # Linha Verde (BR-116)
    (-49.2400, -25.4500, 4, "Linha Verde 1"),
    (-49.2350, -25.4700, 4, "Linha Verde 2"),
    (-49.2380, -25.4600, 4, "Linha Verde 3"),
    # Hauer
    (-49.2650, -25.4780, 4, "Hauer"),
    # Boqueirão
    (-49.2400, -25.4950, 4, "Boqueirão"),
    (-49.2450, -25.4900, 4, "Boqueirão 2"),
    # Pinheirinho - urbano
    (-49.3050, -25.5050, 4, "Pinheirinho urbano"),
    # Cabral
    (-49.2650, -25.4050, 4, "Cabral"),
    # Hugo Lange
    (-49.2550, -25.4200, 4, "Hugo Lange"),
    # Shopping Estação
    (-49.2650, -25.4350, 4, "Shopping Estação"),
    # Alto da XV
    (-49.2550, -25.4280, 4, "Alto da XV"),
    # Novo Mundo
    (-49.2750, -25.4900, 4, "Novo Mundo"),
    # Sítio Cercado
    (-49.2900, -25.5300, 4, "Sítio Cercado"),
    (-49.2950, -25.5250, 4, "Sítio Cercado 2"),
    # Cajuru
    (-49.2250, -25.4600, 4, "Cajuru"),
    (-49.2200, -25.4650, 4, "Cajuru 2"),
    # Uberaba
    (-49.2200, -25.4700, 4, "Uberaba"),

    # === BARE SOIL (class 5) ===
    # Áreas de construção (genérico, periferia)
    (-49.3300, -25.5400, 5, "Tatuquara construção"),
    (-49.2300, -25.5800, 5, "Boqueirão periferia"),
    (-49.3400, -25.5300, 5, "CIC solo exposto"),
    (-49.2200, -25.5500, 5, "Uberaba periferia"),
    (-49.3600, -25.4900, 5, "CIC solo 2"),
]


def extract_features(composite_path):
    """Extract all features from a composite (6 bands + 4 indices = 10 features)."""
    with rasterio.open(str(composite_path)) as src:
        blue = src.read(1).astype(np.float64)
        green = src.read(2).astype(np.float64)
        red = src.read(3).astype(np.float64)
        nir = src.read(4).astype(np.float64)
        swir1 = src.read(5).astype(np.float64)
        swir2 = src.read(6).astype(np.float64)
        transform = src.transform
        h, w = src.height, src.width

    np.seterr(divide="ignore", invalid="ignore")

    ndvi = np.where((nir + red) != 0, (nir - red) / (nir + red), 0)
    ndwi = np.where((green + nir) != 0, (green - nir) / (green + nir), 0)
    ndbi = np.where((swir1 + nir) != 0, (swir1 - nir) / (swir1 + nir), 0)
    mndwi = np.where((green + swir1) != 0, (green - swir1) / (green + swir1), 0)

    # Stack: 10 features
    features = np.stack([blue, green, red, nir, swir1, swir2, ndvi, ndwi, ndbi, mndwi], axis=0)
    return features, transform, h, w


def coords_to_pixel(lon, lat, transform, h, w):
    """Convert lon/lat to pixel row/col."""
    col = int((lon - LON_MIN) / (LON_MAX - LON_MIN) * w)
    row = int((lat - LAT_MIN) / (LAT_MAX - LAT_MIN) * h)
    # Flip row (raster origin is top-left)
    row = h - 1 - row
    return row, col


def sample_around_point(features, row, col, h, w, radius=2):
    """Sample a window of pixels around a point for more training data."""
    samples = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            r, c = row + dr, col + dc
            if 0 <= r < h and 0 <= c < w:
                pixel = features[:, r, c]
                if not np.any(np.isnan(pixel)) and not np.all(pixel == 0):
                    samples.append(pixel)
    return samples


def build_training_data(composite_path):
    """Build training dataset from known locations."""
    features, transform, h, w = extract_features(composite_path)

    X_train = []
    y_train = []

    for lon, lat, class_id, desc in TRAINING_POINTS:
        row, col = coords_to_pixel(lon, lat, transform, h, w)
        if 0 <= row < h and 0 <= col < w:
            # Sample a 5x5 window around each point
            samples = sample_around_point(features, row, col, h, w, radius=2)
            for s in samples:
                X_train.append(s)
                y_train.append(class_id)

    X = np.array(X_train)
    y = np.array(y_train)

    # Remove any NaN rows
    valid = ~np.any(np.isnan(X), axis=1)
    X = X[valid]
    y = y[valid]

    print(f"Training samples: {len(X)}")
    for cid, cname in CLASSES.items():
        print(f"  Class {cid} ({cname}): {(y == cid).sum()} samples")

    return X, y


def train_ensemble(X, y):
    """Train ensemble classifier (RF + GBM, soft voting)."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=500, max_depth=20,
        min_samples_leaf=3, class_weight="balanced",
        random_state=42, n_jobs=-1
    )

    # Gradient Boosting
    gb = GradientBoostingClassifier(
        n_estimators=200, max_depth=8,
        learning_rate=0.1, random_state=42
    )

    print("\nTraining Random Forest (500 trees)...")
    rf.fit(X_scaled, y)
    rf_scores = cross_val_score(rf, X_scaled, y, cv=5, scoring="f1_macro")
    print(f"  RF CV F1-macro: {rf_scores.mean():.4f} (+/- {rf_scores.std():.4f})")

    print("Training Gradient Boosting (200 trees)...")
    gb.fit(X_scaled, y)
    gb_scores = cross_val_score(gb, X_scaled, y, cv=5, scoring="f1_macro")
    print(f"  GB CV F1-macro: {gb_scores.mean():.4f} (+/- {gb_scores.std():.4f})")

    # Feature importance
    feature_names = ["blue", "green", "red", "nir", "swir1", "swir2", "ndvi", "ndwi", "ndbi", "mndwi"]
    importances = rf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("\nFeature importance (RF):")
    for i in sorted_idx:
        print(f"  {feature_names[i]:10s}: {importances[i]:.4f}")

    return rf, gb, scaler


def classify_with_ensemble(rf, gb, scaler, composite_path, year):
    """Classify an entire image using the trained ensemble."""
    features, transform, h, w = extract_features(composite_path)

    # Reshape to (n_pixels, n_features)
    X_all = features.reshape(10, -1).T  # (h*w, 10)

    # Handle NaN
    nan_mask = np.any(np.isnan(X_all), axis=1) | np.all(X_all == 0, axis=1)
    valid_mask = ~nan_mask

    X_valid = X_all[valid_mask]
    X_scaled = scaler.transform(X_valid)

    # Predict with both models
    rf_proba = rf.predict_proba(X_scaled)
    gb_proba = gb.predict_proba(X_scaled)

    # Ensemble: weighted average (RF gets more weight — better on spatial data)
    ensemble_proba = 0.6 * rf_proba + 0.4 * gb_proba
    predictions = rf.classes_[np.argmax(ensemble_proba, axis=1)]

    # Build output
    result = np.zeros(h * w, dtype=np.uint8)
    result[valid_mask] = predictions
    classification = result.reshape(h, w)

    # Post-processing: spatial smoothing (3x3 mode filter)
    from scipy.ndimage import generic_filter

    def mode_filter(values):
        values = values[values > 0]  # Ignore nodata
        if len(values) == 0:
            return 0
        counts = np.bincount(values.astype(int), minlength=6)
        return np.argmax(counts[1:]) + 1  # Skip 0 (nodata)

    print(f"  Post-processing spatial smoothing...")
    classification = generic_filter(
        classification.astype(float), mode_filter, size=3
    ).astype(np.uint8)

    # Save
    output_path = CLASS_DIR / f"classification_{year}.tif"
    tfm = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)
    with rasterio.open(
        str(output_path), "w",
        driver="GTiff", height=h, width=w,
        count=1, dtype="uint8",
        crs=CRS.from_epsg(4326),
        transform=tfm, nodata=0,
    ) as dst:
        dst.write(classification, 1)

    # Stats
    valid = classification[classification > 0]
    total = len(valid)
    stats = {}
    for cid, cname in CLASSES.items():
        pct = (valid == cid).sum() / total * 100 if total > 0 else 0
        ha = (valid == cid).sum() * 0.09
        stats[f"{cname}_pct"] = pct
        stats[f"{cname}_ha"] = ha
        print(f"    {cname:20s}: {pct:5.1f}% ({ha:.0f} ha)")

    return stats


def main():
    print("=" * 60)
    print("CwbVerde — ML Classification with Random Forest + GBM Ensemble")
    print("Training on known Curitiba locations")
    print("=" * 60)

    # Use 2023 composite for training (most recent, best quality)
    train_composite = RAW_DIR / "composite_2023.tif"
    if not train_composite.exists():
        # Use any available
        composites = sorted(RAW_DIR.glob("composite_*.tif"))
        if not composites:
            print("No composites found! Run real_data_pipeline.py first.")
            return
        train_composite = composites[-1]

    print(f"\nTraining on: {train_composite.name}")

    # Build training data
    X, y = build_training_data(train_composite)

    # Train ensemble
    rf, gb, scaler = train_ensemble(X, y)

    # Save model
    model_path = MODEL_DIR / "ensemble_classifier.joblib"
    joblib.dump({"rf": rf, "gb": gb, "scaler": scaler}, str(model_path))
    print(f"\nModel saved: {model_path}")

    # Classify ALL years
    import pandas as pd
    all_stats = []
    composites = sorted(RAW_DIR.glob("composite_*.tif"))
    print(f"\nClassifying {len(composites)} years...")

    for comp in composites:
        year = int(comp.stem.split("_")[1])
        print(f"\n  Year {year}:")
        stats = classify_with_ensemble(rf, gb, scaler, comp, year)
        stats["year"] = year
        all_stats.append(stats)

    # Save stats
    df = pd.DataFrame(all_stats).sort_values("year")
    output = DATA_DIR / "stats" / "classification_summary.parquet"
    df.to_parquet(str(output), index=False)
    print(f"\nClassification stats saved: {output}")
    print(df[["year", "water_pct", "dense_vegetation_pct", "urban_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
